"""System relationship / timing contract for M1 ADX Quant Pro.

This module is intentionally additive.  It does not replace any original tab,
connector, database, frontend, or backend function.  It creates one small
coordination layer so every tab can see the same app state, data version,
connection health, API health, timing metrics, and database audit trail.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import streamlit as st


MAX_MEMORY_EVENTS = 300
STALE_SECONDS_WARNING = 30 * 60


# ---------------------------------------------------------------------------
# small safe helpers
# ---------------------------------------------------------------------------
def _now_text() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        out = float(value)
        if pd.isna(out):
            return float(default)
        return out
    except Exception:
        return float(default)


def _safe_len(value: Any) -> int:
    try:
        return int(len(value))
    except Exception:
        return 0


def _safe_session_setdefault(key: str, value: Any) -> Any:
    if key not in st.session_state:
        st.session_state[key] = value
    return st.session_state[key]


def _trim_events() -> None:
    events = st.session_state.get("system_events", [])
    if not isinstance(events, list):
        events = []
    st.session_state.system_events = events[:MAX_MEMORY_EVENTS]


def _append_memory_event(layer: str, action: str, status: str = "OK", detail: str = "", **extra: Any) -> Dict[str, Any]:
    event = {
        "time": _now_text(),
        "layer": str(layer or "system"),
        "action": str(action or "event"),
        "status": str(status or "OK"),
        "detail": str(detail or ""),
        "tab": st.session_state.get("tab_choice", "Home"),
        "symbol": st.session_state.get("symbol", "XAUUSD"),
        "timeframe": st.session_state.get("timeframe", "M1"),
        "source": st.session_state.get("source", "DISCONNECTED"),
        "data_version": int(st.session_state.get("data_version", 0) or 0),
    }
    for k, v in extra.items():
        try:
            event[str(k)] = v
        except Exception:
            pass
    events = st.session_state.get("system_events", [])
    if not isinstance(events, list):
        events = []
    events.insert(0, event)
    st.session_state.system_events = events[:MAX_MEMORY_EVENTS]
    return event


def record_system_event(layer: str, action: str, status: str = "OK", detail: str = "", persist: bool = False, **extra: Any) -> Dict[str, Any]:
    """Record an app-level event safely.

    persist=False by default because this can be called on every rerun.  Use
    persist=True for meaningful events like connector load, tab error, snapshot,
    or user maintenance actions.
    """
    event = _append_memory_event(layer, action, status, detail, **extra)
    if persist:
        try:
            from core.database import append_csv
            append_csv("system_events", event)
        except Exception:
            pass
    return event


# ---------------------------------------------------------------------------
# startup / session contract
# ---------------------------------------------------------------------------
def init_system_contract() -> Dict[str, Any]:
    """Create the shared runtime contract used by all tabs."""
    _safe_session_setdefault("system_boot_id", uuid.uuid4().hex[:12])
    _safe_session_setdefault("system_boot_time", _now_text())
    _safe_session_setdefault("app_cycle", 0)
    _safe_session_setdefault("data_version", 0)
    _safe_session_setdefault("data_version_source", "startup")
    _safe_session_setdefault("system_events", [])
    _safe_session_setdefault("tab_timing", {})
    _safe_session_setdefault("tab_runtime_current", {})
    _safe_session_setdefault("api_health", {})
    _safe_session_setdefault("frontend_health", {})
    _safe_session_setdefault("backend_health", {})
    _safe_session_setdefault("last_connection_error", "")
    _safe_session_setdefault("last_connection_message", "")
    _safe_session_setdefault("last_connection_rows", 0)
    _safe_session_setdefault("last_connection_mode", "fallback")
    _safe_session_setdefault("last_connected_symbol", st.session_state.get("symbol", "XAUUSD"))
    _safe_session_setdefault("last_connected_timeframe", st.session_state.get("timeframe", "M1"))
    _safe_session_setdefault("last_data_quality", {})
    _safe_session_setdefault("uiux_density", "phone" if st.session_state.get("phone_mode") else "wide")
    _safe_session_setdefault("system_snapshot_autosave", True)

    try:
        st.session_state.app_cycle = int(st.session_state.get("app_cycle", 0) or 0) + 1
    except Exception:
        st.session_state.app_cycle = 1

    contract = build_system_contract()
    st.session_state.system_contract = contract
    return contract


def build_system_contract() -> Dict[str, Any]:
    df = st.session_state.get("last_df")
    data_rows = _safe_len(df) if isinstance(df, pd.DataFrame) else 0
    connected = bool(st.session_state.get("connected", False))
    last_fetch = _safe_float(st.session_state.get("last_fetch", 0), 0.0)
    data_age = max(0.0, time.time() - last_fetch) if last_fetch else None

    return {
        "boot_id": st.session_state.get("system_boot_id", ""),
        "boot_time": st.session_state.get("system_boot_time", ""),
        "cycle": int(st.session_state.get("app_cycle", 0) or 0),
        "active_tab": st.session_state.get("tab_choice", "Home"),
        "frontend": {
            "phone_mode": bool(st.session_state.get("phone_mode", False)),
            "density": st.session_state.get("uiux_density", "wide"),
            "sidebar": "global connector only",
            "safe_page_wrapper": True,
        },
        "backend": {
            "shared_dataframe_key": "last_df",
            "shared_account_key": "account_snapshot",
            "shared_positions_key": "doo_positions",
            "safe_exception_wrapper": True,
        },
        "connection": {
            "connected": connected,
            "source": st.session_state.get("source", "DISCONNECTED"),
            "mode": st.session_state.get("connector_mode", "fallback"),
            "symbol": st.session_state.get("symbol", "XAUUSD"),
            "timeframe": st.session_state.get("timeframe", "M1"),
            "rows": data_rows,
            "data_version": int(st.session_state.get("data_version", 0) or 0),
            "age_seconds": data_age,
            "last_message": st.session_state.get("last_connection_message", ""),
            "last_error": st.session_state.get("last_connection_error", ""),
        },
        "database": {
            "csv_json_kept": True,
            "sqlite_event_mirror": True,
            "safe_backup_before_delete": True,
        },
        "api": st.session_state.get("api_health", {}),
        "timing": st.session_state.get("tab_timing", {}),
    }


# ---------------------------------------------------------------------------
# dataframe quality / connection tracking
# ---------------------------------------------------------------------------
def inspect_market_dataframe(df: Optional[pd.DataFrame], timeframe: str = "M1") -> Dict[str, Any]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "rows": 0,
            "status": "NO_DATA",
            "score": 0,
            "message": "No shared dataframe loaded.",
            "missing_columns": ["time", "open", "high", "low", "close"],
            "duplicates": 0,
            "nan_cells": 0,
            "first_time": "",
            "last_time": "",
            "gap_warning": "",
        }

    d = df.copy()
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in d.columns]
    nan_cells = int(d[required].isna().sum().sum()) if not missing else int(d.isna().sum().sum())
    duplicates = 0
    first_time = ""
    last_time = ""
    gap_warning = ""

    if "time" in d.columns:
        d["time"] = pd.to_datetime(d["time"], errors="coerce")
        d = d.dropna(subset=["time"]).sort_values("time")
        duplicates = int(d["time"].duplicated().sum())
        if not d.empty:
            first_time = str(d["time"].iloc[0])[:19]
            last_time = str(d["time"].iloc[-1])[:19]
            try:
                deltas = d["time"].diff().dropna().dt.total_seconds()
                if len(deltas) >= 5:
                    median_sec = float(deltas.median())
                    max_sec = float(deltas.max())
                    if median_sec > 0 and max_sec > median_sec * 8:
                        gap_warning = f"Large candle gap detected: max {int(max_sec)}s vs median {int(median_sec)}s"
            except Exception:
                pass

    score = 100
    if missing:
        score -= 45
    if _safe_len(d) < 100:
        score -= 20
    if duplicates:
        score -= 10
    if nan_cells:
        score -= 10
    if gap_warning:
        score -= 10
    score = max(0, min(100, score))

    if score >= 85:
        status = "GOOD"
        message = "Shared dataframe is clean enough for all tabs."
    elif score >= 60:
        status = "CHECK"
        message = "Data works, but there are quality warnings."
    else:
        status = "WEAK"
        message = "Data may be unreliable; refresh or change source before relying on analysis."

    return {
        "rows": int(_safe_len(d)),
        "status": status,
        "score": int(score),
        "message": message,
        "missing_columns": missing,
        "duplicates": int(duplicates),
        "nan_cells": int(nan_cells),
        "first_time": first_time,
        "last_time": last_time,
        "gap_warning": gap_warning,
        "timeframe": str(timeframe or "M1"),
    }


def mark_data_version(source: str = "unknown", rows: Optional[int] = None) -> int:
    try:
        st.session_state.data_version = int(st.session_state.get("data_version", 0) or 0) + 1
    except Exception:
        st.session_state.data_version = 1
    st.session_state.data_version_source = str(source or "unknown")
    if rows is not None:
        st.session_state.last_connection_rows = int(rows or 0)
    return int(st.session_state.data_version)


def update_connection_health(
    *,
    mode: str,
    source: str,
    ok: bool,
    message: str = "",
    rows: int = 0,
    symbol: str = "",
    timeframe: str = "",
    persist: bool = True,
) -> Dict[str, Any]:
    health = {
        "checked_at": _now_text(),
        "mode": str(mode or "fallback"),
        "source": str(source or "UNKNOWN"),
        "ok": bool(ok),
        "message": str(message or ""),
        "rows": int(rows or 0),
        "symbol": str(symbol or st.session_state.get("symbol", "XAUUSD")),
        "timeframe": str(timeframe or st.session_state.get("timeframe", "M1")),
        "data_version": int(st.session_state.get("data_version", 0) or 0),
    }
    st.session_state.last_connection_mode = health["mode"]
    st.session_state.last_connection_message = health["message"]
    st.session_state.last_connection_rows = health["rows"]
    st.session_state.last_connected_symbol = health["symbol"]
    st.session_state.last_connected_timeframe = health["timeframe"]
    st.session_state.last_connection_error = "" if ok else health["message"]
    st.session_state.api_health = health

    record_system_event(
        "connection",
        "connect/refresh",
        "OK" if ok else "WARN",
        health["message"],
        persist=persist,
        rows=health["rows"],
        mode=health["mode"],
        source=health["source"],
    )
    return health


def update_data_quality_from_session(persist: bool = False) -> Dict[str, Any]:
    q = inspect_market_dataframe(st.session_state.get("last_df"), st.session_state.get("timeframe", "M1"))
    q["checked_at"] = _now_text()
    q["data_version"] = int(st.session_state.get("data_version", 0) or 0)
    st.session_state.last_data_quality = q
    if persist:
        try:
            from core.database import append_csv
            append_csv("data_quality_events", q)
        except Exception:
            pass
    return q


# ---------------------------------------------------------------------------
# tab timing / frontend-backend timing relation
# ---------------------------------------------------------------------------
def start_tab_timing(tab_name: str) -> float:
    start = time.perf_counter()
    st.session_state.tab_runtime_current = {
        "tab": str(tab_name or "Unknown"),
        "started_perf": start,
        "started_at": _now_text(),
        "data_version": int(st.session_state.get("data_version", 0) or 0),
    }
    return start


def finish_tab_timing(tab_name: str, start_perf: Optional[float] = None, ok: bool = True, error: str = "") -> Dict[str, Any]:
    if start_perf is None:
        current = st.session_state.get("tab_runtime_current", {})
        start_perf = _safe_float(current.get("started_perf"), time.perf_counter()) if isinstance(current, dict) else time.perf_counter()
    elapsed_ms = round(max(0.0, (time.perf_counter() - float(start_perf)) * 1000.0), 2)
    tab = str(tab_name or "Unknown")
    timing = st.session_state.get("tab_timing", {})
    if not isinstance(timing, dict):
        timing = {}
    old = timing.get(tab, {}) if isinstance(timing.get(tab, {}), dict) else {}
    count = int(old.get("count", 0) or 0) + 1
    avg_ms = round(((float(old.get("avg_ms", 0) or 0) * (count - 1)) + elapsed_ms) / max(count, 1), 2)
    row = {
        "tab": tab,
        "ok": bool(ok),
        "last_ms": elapsed_ms,
        "avg_ms": avg_ms,
        "count": count,
        "last_run": _now_text(),
        "error": str(error or ""),
        "data_version": int(st.session_state.get("data_version", 0) or 0),
    }
    timing[tab] = row
    st.session_state.tab_timing = timing

    if (not ok) or elapsed_ms > 2500:
        record_system_event(
            "tab",
            f"render {tab}",
            "ERROR" if not ok else "SLOW",
            str(error or f"slow render {elapsed_ms} ms"),
            persist=True,
            elapsed_ms=elapsed_ms,
        )
    return row


def timing_dataframe() -> pd.DataFrame:
    timing = st.session_state.get("tab_timing", {})
    if not isinstance(timing, dict) or not timing:
        return pd.DataFrame(columns=["tab", "ok", "last_ms", "avg_ms", "count", "last_run", "error", "data_version"])
    return pd.DataFrame(list(timing.values())).sort_values(["ok", "last_ms"], ascending=[True, False]).reset_index(drop=True)


def system_events_dataframe(limit: int = 100) -> pd.DataFrame:
    events = st.session_state.get("system_events", [])
    if not isinstance(events, list):
        events = []
    return pd.DataFrame(events[: int(limit or 100)])


# ---------------------------------------------------------------------------
# renderers: all safe, no original logic replacement
# ---------------------------------------------------------------------------
def _status_badge_html(text: str, status: str) -> str:
    status = str(status or "info").upper()
    if status in ["GOOD", "OK", "LIVE", "READY"]:
        cls = "rel-ok"
    elif status in ["CHECK", "WARN", "SLOW"]:
        cls = "rel-warn"
    elif status in ["WEAK", "ERROR", "NO_DATA", "DISCONNECTED"]:
        cls = "rel-bad"
    else:
        cls = "rel-info"
    return f'<span class="rel-badge {cls}">{text}</span>'


def render_relationship_matrix(location: str = "global", compact: bool = False) -> None:
    contract = build_system_contract()
    q = update_data_quality_from_session(persist=False)
    conn = contract.get("connection", {})
    api = st.session_state.get("api_health", {}) if isinstance(st.session_state.get("api_health", {}), dict) else {}
    timing = timing_dataframe()

    connected = bool(conn.get("connected")) and int(conn.get("rows") or 0) > 0
    source_name = str(conn.get("source", "DISCONNECTED") or "DISCONNECTED").upper()
    if not connected:
        conn_status = "DISCONNECTED"
    elif source_name in ["SAFE_DEMO", "CACHE"]:
        conn_status = "WARN"
    else:
        conn_status = "OK"
    data_status = str(q.get("status", "NO_DATA"))
    if source_name in ["SAFE_DEMO", "CACHE"]:
        api_status = "WARN"
    else:
        api_status = "OK" if api.get("ok") else ("WARN" if api else "WAIT")
    timing_status = "OK"
    if not timing.empty and (timing["ok"].astype(str).str.lower() == "false").any():
        timing_status = "ERROR"
    elif not timing.empty and float(timing["last_ms"].max()) > 2500:
        timing_status = "SLOW"

    api_message = str(api.get("message", "waiting") or "waiting")[:60]

    st.markdown(
        f"""
        <div class="rel-card">
          <div class="rel-title">🔗 System Relationship + Timing</div>
          <div class="rel-grid">
            <div><b>Frontend / UIUX</b><span>{'Phone' if contract['frontend']['phone_mode'] else 'Laptop'} layout</span>{_status_badge_html('READY', 'OK')}</div>
            <div><b>Global Connection</b><span>{conn.get('source','DISCONNECTED')} • {conn.get('rows',0):,} rows</span>{_status_badge_html(conn_status, conn_status)}</div>
            <div><b>Shared Dataframe</b><span>version {conn.get('data_version',0)} • quality {q.get('score',0)}/100</span>{_status_badge_html(data_status, data_status)}</div>
            <div><b>Backend Functions</b><span>safe wrapper + shared state</span>{_status_badge_html('READY', 'OK')}</div>
            <div><b>Database</b><span>CSV/JSON + SQLite event mirror</span>{_status_badge_html('READY', 'OK')}</div>
            <div><b>API Health</b><span>{api.get('mode', conn.get('mode','fallback'))} • {api_message}</span>{_status_badge_html(api_status, api_status)}</div>
            <div><b>Tab Timing</b><span>{len(timing)} tracked tab(s)</span>{_status_badge_html(timing_status, timing_status)}</div>
            <div><b>Auto Refresh</b><span>{st.session_state.get('refresh_seconds',600)}s backend / 10m app</span>{_status_badge_html('SYNC', 'OK')}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not compact:
        with st.expander("Open detailed relationship diagnostics", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Data Version", conn.get("data_version", 0))
            c2.metric("Rows", f"{int(conn.get('rows') or 0):,}")
            c3.metric("Quality", f"{q.get('score',0)}/100")
            c4.metric("Render Cycle", contract.get("cycle", 0))
            st.caption(q.get("message", ""))
            if q.get("gap_warning"):
                st.warning(q.get("gap_warning"))
            if q.get("missing_columns"):
                st.caption("Missing columns: " + ", ".join(q.get("missing_columns") or []))
            if not timing.empty:
                st.dataframe(timing, use_container_width=True, hide_index=True, height=220)
            events = system_events_dataframe(30)
            if not events.empty:
                st.dataframe(events, use_container_width=True, hide_index=True, height=220)


def render_sidebar_mini_contract() -> None:
    q = st.session_state.get("last_data_quality", {})
    if not isinstance(q, dict) or not q:
        q = update_data_quality_from_session(False)
    rows = _safe_len(st.session_state.get("last_df")) if isinstance(st.session_state.get("last_df"), pd.DataFrame) else 0
    source = st.session_state.get("source", "DISCONNECTED")
    status = q.get("status", "NO_DATA")
    st.markdown(
        f"""
        <div class="rel-mini">
            <b>🔗 Sync</b><br>
            <small>{source} • rows {rows:,} • data v{st.session_state.get('data_version',0)} • quality {q.get('score',0)}/100 ({status})</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def maybe_persist_runtime_snapshot(reason: str = "cycle") -> None:
    """Persist lightweight snapshots, throttled to avoid database spam."""
    if not bool(st.session_state.get("system_snapshot_autosave", True)):
        return
    now = time.time()
    last = _safe_float(st.session_state.get("last_runtime_snapshot_saved", 0), 0.0)
    if now - last < 60:
        return
    try:
        st.session_state.last_runtime_snapshot_saved = now
        q = update_data_quality_from_session(False)
        row = {
            "saved_at": _now_text(),
            "reason": reason,
            "tab": st.session_state.get("tab_choice", "Home"),
            "symbol": st.session_state.get("symbol", "XAUUSD"),
            "timeframe": st.session_state.get("timeframe", "M1"),
            "source": st.session_state.get("source", "DISCONNECTED"),
            "connected": bool(st.session_state.get("connected", False)),
            "rows": _safe_len(st.session_state.get("last_df")) if isinstance(st.session_state.get("last_df"), pd.DataFrame) else 0,
            "data_version": int(st.session_state.get("data_version", 0) or 0),
            "quality_score": q.get("score", 0),
            "quality_status": q.get("status", "NO_DATA"),
            "app_cycle": int(st.session_state.get("app_cycle", 0) or 0),
        }
        from core.database import append_csv
        append_csv("runtime_snapshots", row)
    except Exception:
        pass
