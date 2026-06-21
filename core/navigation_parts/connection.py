import time
import streamlit as st

from core.common import DEFAULT_TABS, log_event
from core.styles import request_close_sidebar
from core.ui_relationship import mark_navigation, sync_shared_connection_signature
from core.ui.effects import queue_ui_popup
from core.data_connectors import manual_connect
from core.websocket_feed import render_websocket_panel, websocket_status
from core.system_upgrade import sidebar_health_card, add_snapshot_button
from core.system_contract import render_sidebar_mini_contract, record_system_event
from core.system_relations import render_system_relation_hub
from core.global_upgrade import render_sidebar_upgrade_panel, render_sidebar_pro_header, data_quality, get_live_df
from core.ui.compact import render_metric_cards

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs):
        return None


from .state import _safe_log_event

def _read_account_after_live_connect(source: str):
    """After MT5/Doo Bridge market candles connect, also pull account/positions.

    This makes the sidebar Doo Prime/MT5 connection useful immediately instead
    of leaving the account area empty until a separate Home button is pressed.
    """
    try:
        source_u = str(source or "").upper()
        if source_u not in ["MT5", "DOO_BRIDGE"]:
            return
        from core.data_connectors import get_mt5_account_snapshot
        if source_u == "DOO_BRIDGE":
            snap = get_mt5_account_snapshot(
                bridge_url=st.session_state.get("doo_bridge_url", ""),
                bridge_token=st.session_state.get("doo_bridge_token", ""),
            )
        else:
            snap = get_mt5_account_snapshot()
        if snap.get("ok"):
            info = dict(snap.get("account", {}) or {})
            info["positions"] = snap.get("positions", []) or []
            st.session_state.account_snapshot = info
            st.session_state.doo_positions = info.get("positions", [])
            st.caption(f"🏦 Account snapshot loaded: {len(info.get('positions', []) or []):,} open positions")
        else:
            st.caption(f"Account read not ready: {snap.get('message', '')}")
    except Exception as exc:
        st.caption(f"Account auto-read skipped safely: {exc}")

def _connect_now(label="Refresh", quick=False):
    """One-click idempotent shared connector action with persistent state."""
    from core.connector_state_machine_20260621 import begin, fail, succeed
    prefix = "market_connector_20260621"
    if not begin(st.session_state, prefix):
        st.info("A market connection request is already in progress; the duplicate click was ignored.")
        return {"ok": False, "duplicate_blocked": True, "state": "CONNECTING"}
    outcome = {"ok": False, "state": "CONNECTING"}
    try:
        bars = 600 if quick else int(st.session_state.get("connector_bars", 600))
        timeframe = str(st.session_state.get("timeframe", "M1") or "M1").upper()
        mode = st.session_state.get("connector_mode", "mt5")
        allow_demo = bool(st.session_state.get("allow_safe_demo", False))
        if timeframe == "CUSTOM":
            # CUSTOM is a timeframe choice, not a connector. It loads H1 and M1 separately.
            # H1 remains the main shared dataframe; M1 is stored only for confirmation/pullback timing.
            with st.spinner(f"{label}: loading {st.session_state.symbol} CUSTOM = H1 main + M1 confirmation..."):
                h1_df, h1_ok, h1_source, h1_msg = manual_connect(
                    mode=mode,
                    symbol=st.session_state.get("symbol", "EURUSD"),
                    api_key=st.session_state.get("twelve_api_key", ""),
                    bars=bars,
                    timeframe="H1",
                    bridge_url=st.session_state.get("doo_bridge_url", ""),
                    bridge_token=st.session_state.get("doo_bridge_token", ""),
                    allow_demo=allow_demo,
                )
                m1_df, m1_ok, m1_source, m1_msg = manual_connect(
                    mode=mode,
                    symbol=st.session_state.get("symbol", "EURUSD"),
                    api_key=st.session_state.get("twelve_api_key", ""),
                    bars=max(int(bars), 1500),
                    timeframe="M1",
                    bridge_url=st.session_state.get("doo_bridge_url", ""),
                    bridge_token=st.session_state.get("doo_bridge_token", ""),
                    allow_demo=allow_demo,
                )
            df, ok, source, msg = h1_df, bool(h1_ok), f"CUSTOM_H1_MAIN_{h1_source}", f"H1: {h1_msg} | M1: {m1_msg}"
            if h1_ok:
                st.session_state.custom_h1_df = h1_df
                st.session_state.last_df = h1_df
            if m1_ok:
                st.session_state.custom_m1_df = m1_df
            st.session_state.timeframe = "CUSTOM"
        else:
            with st.spinner(f"{label}: loading {st.session_state.symbol} {timeframe} {bars:,} candles..."):
                df, ok, source, msg = manual_connect(
                    mode=mode,
                    symbol=st.session_state.get("symbol", "EURUSD"),
                    api_key=st.session_state.get("twelve_api_key", ""),
                    bars=bars,
                    timeframe=timeframe,
                    bridge_url=st.session_state.get("doo_bridge_url", ""),
                    bridge_token=st.session_state.get("doo_bridge_token", ""),
                    allow_demo=allow_demo,
                )
        source_u = str(source or "").upper()
        if ok and source_u == "SAFE_DEMO":
            st.warning(f"SAFE_DEMO loaded: {len(df):,} rows. Use only for UI testing, not real trade exits.")
        elif ok:
            st.success(f"{source}: {len(df):,} rows loaded")
            queue_ui_popup("Shared data updated", f"{source}: {len(df):,} rows loaded", "success")
            sync_shared_connection_signature()
            st.toast(f"Shared data updated: {source} / {len(df):,} rows", icon="✅")
            _read_account_after_live_connect(source)
            # Keep Doo Prime Analysis + Data Modeling synchronized with the same sidebar refresh.
            # This is fast: it rebuilds deep M1/H1 blocks from the already-loaded shared dataframe
            # instead of making the user press a second refresh button inside Home.
            try:
                from tabs.home_split.doo_prime_deep import refresh_deep_doo_from_shared
                refresh_deep_doo_from_shared()
                st.session_state.doo_deep_auto_fetch = True
                st.session_state.doo_data_modeling_ready = True
            except Exception as deep_exc:
                st.session_state.doo_deep_sync_warning = str(deep_exc)
        else:
            queue_ui_popup("Connection failed", str(msg)[:120], "danger")
            st.error(str(msg))
        if ok:
            message = f"{source}: {len(df):,} rows loaded"
            succeed(st.session_state, prefix, message)
            outcome = {"ok": True, "state": "CONNECTED", "source": str(source), "rows": int(len(df)), "message": message}
        else:
            fail(st.session_state, prefix, str(msg))
            outcome = {"ok": False, "state": "ERROR", "source": str(source), "rows": 0, "message": str(msg)[:300]}
    except Exception as exc:
        safe_message = f"{label} failed: {exc}"
        fail(st.session_state, prefix, safe_message)
        outcome = {"ok": False, "state": "ERROR", "message": safe_message[:300]}
        st.error(safe_message)
    finally:
        # 2026-06-14 hard sidebar close after Connect/Refresh.
        try:
            request_close_sidebar()
        except Exception:
            pass
    return outcome

