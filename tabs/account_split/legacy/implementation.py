import time
import streamlit as st
import pandas as pd
import numpy as np

# ==========================================================
# SAFE IMPORTS
# ==========================================================

try:
    from core.common import DEFAULT_TABS, log_event
except Exception:
    DEFAULT_TABS = ["home", "engine", "backtest", "guide", "account"]

    def log_event(*args, **kwargs):
        return None

try:
    from core.styles import request_close_sidebar
except Exception:
    def request_close_sidebar(*args, **kwargs):
        return None

try:
    from core.data_connectors import manual_connect, mt5_account_info, fetch_mt5
except Exception:
    manual_connect = None
    mt5_account_info = None
    fetch_mt5 = None

try:
    from core.quant_models import quant_stack
except Exception:
    quant_stack = None

try:
    from core.database import append_csv, read_csv
except Exception:
    append_csv = None
    read_csv = None

try:
    from core.ui_helpers import choice_buttons
except Exception:
    def choice_buttons(label, options, key, columns=4, default=None, help_text=""):
        options = list(options or [])
        if not options:
            return ""
        if key not in st.session_state or st.session_state.get(key) not in options:
            st.session_state[key] = default if default in options else options[0]
        if label:
            st.caption(label)
        cols = st.columns(min(max(1, int(columns or 4)), len(options)))
        for i, opt in enumerate(options):
            with cols[i % len(cols)]:
                if st.button(("✅ " if st.session_state.get(key) == opt else "") + str(opt), key=f"{key}_{i}", use_container_width=True):
                    st.session_state[key] = opt
                    st.session_state["ui_navigation_click_ts"] = time.time()
        return st.session_state.get(key, options[0])


# ==========================================================
# SAFE HELPERS
# ==========================================================

def _safe_num(v, default=0.0):
    try:
        if v is None:
            return default
        if isinstance(v, str) and v.strip() == "":
            return default
        v = float(v)
        if not np.isfinite(v):
            return default
        return v
    except Exception:
        return default


def _safe_int(v, default=0):
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _safe_text(v, default=""):
    try:
        if v is None:
            return default
        return str(v)
    except Exception:
        return default


def _safe_append_csv(name, row):
    if append_csv is None:
        return False, "append_csv is unavailable."

    try:
        append_csv(name, row)
        return True, "Saved."
    except Exception as exc:
        return False, f"Save failed: {exc}"


def _safe_read_csv(name):
    if read_csv is None:
        return pd.DataFrame()

    try:
        df = read_csv(name)
        if df is None:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def _safe_log_event(message):
    try:
        log_event(message)
    except Exception:
        pass


def _safe_close_sidebar():
    try:
        request_close_sidebar()
    except Exception:
        pass


def _normalize_account_info(raw):
    """
    Accepts different possible MT5 connector outputs and returns one safe dict.

    Supported:
    - dict account snapshot
    - tuple: info, ok, msg
    - tuple: ok, info, msg
    """
    if raw is None:
        return {}, False, "No MT5 account data returned."

    if isinstance(raw, tuple):
        if len(raw) >= 3:
            a, b, c = raw[0], raw[1], raw[2]

            if isinstance(a, dict):
                return a, bool(b), _safe_text(c, "MT5 account read finished.")

            if isinstance(b, dict):
                return b, bool(a), _safe_text(c, "MT5 account read finished.")

        if len(raw) >= 1 and isinstance(raw[0], dict):
            return raw[0], True, "MT5 account read finished."

    if isinstance(raw, dict):
        ok = bool(raw.get("ok", True))
        msg = raw.get("message", "MT5 account read finished.")
        return raw, ok, msg

    return {}, False, "Unsupported MT5 account response format."


def _safe_mt5_account_info():
    if mt5_account_info is None:
        return {}, False, "mt5_account_info is unavailable. Check core.data_connectors."

    try:
        raw = mt5_account_info()
        info, ok, msg = _normalize_account_info(raw)
        return info, ok, msg
    except Exception as exc:
        return {}, False, f"MT5 account reader crashed safely: {exc}"


def _safe_manual_connect(source, symbol, api_key="", bars=5000, timeframe="M1"):
    if manual_connect is None:
        st.error("manual_connect is unavailable. Check core.data_connectors import.")
        return

    try:
        with st.spinner(f"Connecting {source.upper()} {symbol} {timeframe}..."):
            manual_connect(
                source,
                symbol,
                api_key,
                bars=bars,
                timeframe=timeframe,
            )

        st.success(f"Connected: {source.upper()} {symbol} {timeframe}")
        _safe_rerun()

    except Exception as exc:
        st.error(f"{source.upper()} connection failed safely: {exc}")


def _safe_quant_stack(df):
    if df is None:
        return {
            "bias": "WAIT",
            "scale10": 0,
            "safe_pct": 0,
        }

    if quant_stack is None:
        return {
            "bias": "WAIT",
            "scale10": 0,
            "safe_pct": 0,
            "message": "quant_stack unavailable",
        }

    try:
        q = quant_stack(
            df,
            st.session_state.get("trade_history", []),
            st.session_state.get("account_snapshot", {}),
        )

        if not isinstance(q, dict):
            return {
                "bias": "WAIT",
                "scale10": 0,
                "safe_pct": 0,
                "message": "quant_stack returned invalid output",
            }

        q.setdefault("bias", "WAIT")
        q.setdefault("scale10", 0)
        q.setdefault("safe_pct", 0)

        return q

    except Exception as exc:
        return {
            "bias": "WAIT",
            "scale10": 0,
            "safe_pct": 0,
            "message": f"quant_stack crashed safely: {exc}",
        }


def _save_once_per_60_seconds(name, row, state_key):
    """
    Prevent duplicate CSV spam on every Streamlit rerun.
    """
    now = pd.Timestamp.now()
    last_time = st.session_state.get(state_key)

    should_save = False

    if last_time is None:
        should_save = True
    else:
        try:
            elapsed = (now - pd.to_datetime(last_time)).total_seconds()
            should_save = elapsed >= 60
        except Exception:
            should_save = True

    if should_save:
        ok, msg = _safe_append_csv(name, row)
        if ok:
            st.session_state[state_key] = now
        return ok, msg

    return True, "Skipped duplicate auto-save."




# ==========================================================
# HOME COPY-TO-GPT EXPORT HELPERS
# ==========================================================

def _json_safe(obj):
    try:
        if isinstance(obj, pd.DataFrame):
            return obj.tail(200).to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        if isinstance(obj, (pd.Timestamp,)):
            return str(obj)
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, dict):
            return {str(k): _json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_json_safe(x) for x in obj]
        return obj
    except Exception:
        return str(obj)


def _build_home_copy_payload():
    """Build one clean text report from the current Home tab state so it can be pasted into GPT."""
    df = st.session_state.get("last_df")
    account = st.session_state.get("account_snapshot", {}) or {}
    q = {}
    market = {}
    market_quality = {}
    deep_rows = []

    try:
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            q = _safe_quant_stack(df)
            market, _frame = _calc_market_analytics(df)
            market_quality = {
                "rows_used": len(_frame) if isinstance(_frame, pd.DataFrame) else 0,
                "fat_tail_available": bool((market or {}).get("fat_tail_available", False)),
                "fat_tail_note": (market or {}).get("fat_tail_note", ""),
            }
    except Exception as exc:
        market_quality = {"error": str(exc)}

    try:
        deep = st.session_state.get("doo_deep_results", {}) or {}
        for key, res in deep.items():
            m = (res or {}).get("market", {}) or {}
            deep_rows.append({
                "block": (res or {}).get("label", key),
                "source": (res or {}).get("source", "-"),
                "rows": (res or {}).get("rows", 0),
                "direction": m.get("trend_direction", "WAIT"),
                "regime": m.get("regime", "NO DATA"),
                "dve_pct": m.get("directional_efficiency"),
                "rising_eff_pct": m.get("efficiency_rising"),
                "falling_eff_pct": m.get("efficiency_falling"),
                "fat_tail_z": m.get("fat_tail_z") if m.get("fat_tail_available", False) else "N/A",
                "fat_tail_note": m.get("fat_tail_note", ""),
                "trust_pct": m.get("trust"),
            })
    except Exception:
        pass

    tail_rows = []
    try:
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            cols = [c for c in ["time", "open", "high", "low", "close", "volume"] if c in df.columns]
            if cols:
                tail_rows = df[cols].tail(30).copy().to_dict(orient="records")
    except Exception:
        tail_rows = []

    payload = {
        "export_time": str(pd.Timestamp.now()),
        "symbol": st.session_state.get("symbol", "XAUUSD"),
        "source": st.session_state.get("source", "DISCONNECTED"),
        "timeframe": st.session_state.get("timeframe", "M1"),
        "connector_mode": st.session_state.get("connector_mode", "fallback"),
        "rows": len(df) if isinstance(df, pd.DataFrame) else 0,
        "home_12h_quant_stack": q,
        "advanced_market_analytics": market,
        "market_data_quality": market_quality,
        "emergency_exit_decision": _json_safe(_build_emergency_exit_decision(account, _positions_frame(account), market, q)[0]) if isinstance(account, dict) and account else {},
        "account_snapshot": account,
        "doo_prime_deep_summary": deep_rows,
        "latest_candles_tail_30": tail_rows,
        "instruction_for_gpt": "Use this data to analyze current XAUUSD/selected symbol risk, trend regime, fat-tail shock risk, DVE, margin danger, and 12H hold bias. Do not treat N/A as zero.",
    }

    text = "HOME TAB DATA EXPORT FOR GPT\n" + "=" * 40 + "\n"
    try:
        import json
        text += json.dumps(_json_safe(payload), indent=2, ensure_ascii=False, default=str)
    except Exception:
        text += str(_json_safe(payload))
    return text


def _copy_home_data_box():
    """Render a premium phone-safe browser copy button plus fallback textarea."""
    try:
        import json
        import html
        import re
        import streamlit.components.v1 as components
        text = _build_home_copy_payload()
        text_json = json.dumps(str(text or ""))
        safe_text = html.escape(text)
        components.html(
            f"""
            <style>
            *{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;}}
            .home-copy-card{{padding:12px;border-radius:26px;background:linear-gradient(135deg,rgba(255,255,255,.76),rgba(224,242,254,.52));border:1px solid rgba(125,211,252,.46);box-shadow:0 18px 42px rgba(2,132,199,.15);}}
            .home-copy-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:8px;color:#0f172a;font-weight:950;}}
            .home-copy-pill{{font-size:11px;color:#0f766e;background:rgba(240,253,250,.82);border:1px solid rgba(20,184,166,.22);border-radius:999px;padding:5px 9px;font-weight:900;}}
            .home-copy-btn{{width:100%;min-height:56px;border:0;border-radius:22px;cursor:pointer;color:white;font-size:15px;font-weight:950;background:radial-gradient(circle at 12% 8%,rgba(255,255,255,.42),transparent 24%),linear-gradient(135deg,#0284c7,#06b6d4 52%,#14b8a6);box-shadow:0 18px 36px rgba(2,132,199,.30),inset 0 1px 0 rgba(255,255,255,.50);touch-action:manipulation;-webkit-tap-highlight-color:transparent;}}
            .home-copy-btn:active{{transform:scale(.985)}}.home-copy-status{{margin:7px 0 8px;text-align:center;color:#075985;font-size:12px;font-weight:900;min-height:18px;}}
            .home-copy-text{{width:100%;height:170px;border-radius:18px;border:1px solid rgba(14,116,144,.18);padding:11px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;background:rgba(255,255,255,.78);color:#0f172a;}}
            @media(max-width:520px){{.home-copy-card{{padding:9px;border-radius:22px}}.home-copy-btn{{min-height:60px;font-size:14px}}.home-copy-text{{height:190px;font-size:11.5px}}}}
            </style>
            <div class="home-copy-card">
              <div class="home-copy-head"><span>📋 Home Data Copy Center</span><span class="home-copy-pill">PHONE SAFE</span></div>
              <button id="copyHomeDataBtn" class="home-copy-btn" type="button">Copy all Home tab data for GPT</button>
              <div id="copyHomeDataStatus" class="home-copy-status">Ready • tap once</div>
              <textarea id="homeDataText" class="home-copy-text">{safe_text}</textarea>
            </div>
            <script>
            (function(){{
              const btn=document.getElementById('copyHomeDataBtn');
              const ta=document.getElementById('homeDataText');
              const status=document.getElementById('copyHomeDataStatus');
              const txt={text_json}; ta.value=txt;
              async function copyNow(e){{
                if(e){{e.preventDefault();e.stopPropagation();}}
                let ok=false;
                try{{ if(navigator.clipboard && window.isSecureContext){{ await navigator.clipboard.writeText(txt); ok=true; }} }}catch(err){{ok=false;}}
                if(!ok){{ try{{ ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length); ok=document.execCommand('copy'); ta.blur(); }}catch(err){{ok=false;}} }}
                status.innerText=ok?'Copied ✅ Paste it into GPT now.':'Copy blocked — long-press text below and Select All.';
                if(ok){{btn.innerText='✅ Copied successfully';setTimeout(function(){{btn.innerText='Copy all Home tab data for GPT';}},1400);}}
              }}
              ['pointerup','click','touchend'].forEach(function(evt){{btn.addEventListener(evt,copyNow,{{passive:false}});}});
            }})();
            </script>
            """,
            height=305,
        )
        st.caption("⬇️ Home export download is centralized in the sidebar Download Center. Use copy text for GPT paste workflow.")
    except Exception as exc:
        st.warning(f"Copy box could not load safely: {exc}")

# ==========================================================
# RISK STATUS
# ==========================================================

def _risk_status(label, value):
    v = _safe_num(value)
    label = str(label).lower()

    if label == "margin_level":
        if v <= 0:
            return "UNKNOWN", "No margin level from MT5 yet"
        if v >= 500:
            return "VERY GOOD", "Large margin buffer"
        if v >= 250:
            return "GOOD", "Healthy margin buffer"
        if v >= 150:
            return "BAD", "Margin getting tight"
        return "DANGEROUS", "Margin call danger zone"

    if label == "drawdown":
        if v <= 3:
            return "VERY GOOD", "Very low drawdown"
        if v <= 8:
            return "GOOD", "Normal drawdown"
        if v <= 15:
            return "BAD", "Reduce risk"
        return "DANGEROUS", "High drawdown"

    if label == "margin_used_pct":
        if v <= 15:
            return "VERY GOOD", "Low margin usage"
        if v <= 35:
            return "GOOD", "Manageable usage"
        if v <= 60:
            return "BAD", "High usage"
        return "DANGEROUS", "Too much margin used"

    if label == "floating_pl":
        if v >= 0:
            return "GOOD", "Floating profit"
        return "BAD", "Floating loss; check exposure"

    if label == "free_margin_pct":
        if v >= 75:
            return "VERY GOOD", "Large free margin buffer"
        if v >= 50:
            return "GOOD", "Healthy free margin"
        if v >= 25:
            return "BAD", "Free margin getting low"
        return "DANGEROUS", "Free margin danger zone"

    if label == "open_positions":
        if v <= 3:
            return "VERY GOOD", "Low exposure count"
        if v <= 7:
            return "GOOD", "Manageable exposure count"
        if v <= 12:
            return "BAD", "Many open positions"
        return "DANGEROUS", "Too many open positions"

    return "GOOD", "Normal"


def _metric_status(col, label, value, status_key=None):
    status, note = _risk_status(status_key or str(label).lower(), value)
    col.metric(label, value)
    col.caption(f"{status}: {note}")


# ==========================================================
# POSITION PROCESSING
# ==========================================================

def _position_to_dict(pos):
    if isinstance(pos, dict):
        return pos

    if hasattr(pos, "_asdict"):
        try:
            return pos._asdict()
        except Exception:
            pass

    try:
        return dict(pos)
    except Exception:
        pass

    out = {}

    for key in dir(pos):
        if key.startswith("_"):
            continue

        try:
            value = getattr(pos, key)
            if not callable(value):
                out[key] = value
        except Exception:
            pass

    return out


def _guess_pip_size(symbol, price=None):
    symbol = str(symbol or "").upper()
    price = _safe_num(price)

    if "JPY" in symbol:
        return 0.01

    if "XAU" in symbol or "GOLD" in symbol:
        return 0.1

    if "XAG" in symbol or "SILVER" in symbol:
        return 0.01

    if "BTC" in symbol or "ETH" in symbol:
        return 1.0

    if price >= 100:
        return 0.01

    return 0.0001


def _calc_pips(row):
    price_open = _safe_num(row.get("price_open"))
    price_current = _safe_num(row.get("price_current"))
    symbol = row.get("symbol", "")
    side = str(row.get("side", "")).upper()

    if price_open <= 0 or price_current <= 0:
        return 0.0

    pip_size = _guess_pip_size(symbol, price_open)

    if side == "SELL":
        pips = (price_open - price_current) / pip_size
    else:
        pips = (price_current - price_open) / pip_size

    return round(pips, 1)


def _positions_frame(info):
    positions = info.get("positions", []) if isinstance(info, dict) else []

    if not positions:
        return pd.DataFrame()

    rows = [_position_to_dict(p) for p in positions]

    try:
        df = pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    if "time" in df.columns:
        df["open_time"] = pd.to_datetime(df["time"], unit="s", errors="coerce")

    if "time_update" in df.columns:
        df["update_time"] = pd.to_datetime(df["time_update"], unit="s", errors="coerce")

    for c in ["profit", "volume", "price_open", "price_current", "swap", "commission"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "type" in df.columns:
        df["side"] = df["type"].map({0: "BUY", 1: "SELL"}).fillna(df["type"].astype(str))
    elif "side" not in df.columns:
        df["side"] = "UNKNOWN"

    if "open_time" in df.columns:
        now = pd.Timestamp.now()
        df["hold_minutes"] = (now - df["open_time"]).dt.total_seconds() / 60
        df["hold_hours"] = (df["hold_minutes"] / 60).round(2)

    if "price_open" in df.columns and "price_current" in df.columns:
        df["pips"] = df.apply(_calc_pips, axis=1)

    if "profit" in df.columns and "volume" in df.columns:
        df["profit_per_0.01"] = df.apply(
            lambda r: round(_safe_num(r.get("profit")) / max(_safe_num(r.get("volume")), 0.01) * 0.01, 2),
            axis=1,
        )

    return df




# ==========================================================
# ADVANCED DOO PRIME LIVE ANALYTICS
# ==========================================================

def _status_badge(status):
    status = str(status or "NORMAL").upper()
    if status in ["VERY GOOD", "GOOD", "STRONG", "STARTING", "CONFIRMED"]:
        return "🟢"
    if status in ["WATCH", "LIMIT", "EXHAUSTION", "BAD", "WARNING"]:
        return "🟡"
    if status in ["DANGEROUS", "STOP", "REVERSAL RISK", "EXTREME"]:
        return "🔴"
    return "⚪"


def _analytics_status(label, value, extra=None):
    v = _safe_num(value)
    label = str(label).lower()

    if label == "price_speed_abs_pct_min":
        if v >= 0.30:
            return "EXTREME", "Very fast price expansion; impulse or news-like movement possible."
        if v >= 0.12:
            return "WATCH", "Fast price movement; one-way pressure may be active."
        return "NORMAL", "Price speed is normal or quiet."

    if label == "price_accel_abs":
        if v >= 0.08:
            return "WATCH", "Price change is accelerating compared with the last window."
        return "NORMAL", "No strong acceleration yet."

    if label == "fat_tail_z":
        if v >= 3.0:
            return "EXTREME", "Fat-tail shock: latest move is unusually large versus recent behavior."
        if v >= 2.0:
            return "WATCH", "Large tail move; continuation or snap-back risk is higher."
        return "NORMAL", "Latest move is inside normal recent distribution."

    if label == "directional_efficiency":
        if v >= 80:
            return "STRONG", "Very efficient one-way movement; trend is clean but can be near exhaustion if tail is also high."
        if v >= 60:
            return "STARTING", "Directional movement is becoming one-way."
        if v >= 35:
            return "NORMAL", "Mixed movement; trend exists but with noise."
        return "BAD", "Choppy market; one-way trend is weak."

    if label == "efficiency_rising":
        if v >= 15:
            return "CONFIRMED", "Efficiency is rising strongly; one-way trend may be starting."
        if v >= 5:
            return "STARTING", "Efficiency is improving; watch for trend continuation."
        return "NORMAL", "Efficiency is not rising enough yet."

    if label == "efficiency_falling":
        if v >= 20:
            return "EXHAUSTION", "Efficiency is falling hard; existing one-way trend may be losing power."
        if v >= 8:
            return "LIMIT", "Trend may be reaching limit; protect profit or reduce chasing."
        return "NORMAL", "No strong exhaustion signal from efficiency."

    if label == "margin_level_change":
        if v >= 0:
            return "GOOD", "Margin level is improving."
        if v > -5:
            return "WATCH", "Margin level is slipping slowly."
        return "DANGEROUS", "Margin level is dropping fast; account risk is increasing."

    return "NORMAL", "Normal."


def _get_close_column(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    for c in ["close", "Close", "price", "Price", "bid", "Bid", "last", "Last"]:
        if c in df.columns:
            return c
    nums = df.select_dtypes(include=[np.number]).columns.tolist()
    return nums[-1] if nums else None


def _get_time_column(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    for c in ["time", "Time", "datetime", "Datetime", "date", "Date", "timestamp", "Timestamp"]:
        if c in df.columns:
            return c
    return None


def _prepare_market_frame(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    close_col = _get_close_column(df)
    if close_col is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["price"] = pd.to_numeric(df[close_col], errors="coerce")

    time_col = _get_time_column(df)
    if time_col is not None:
        out["time"] = pd.to_datetime(df[time_col], errors="coerce")
    else:
        out["time"] = pd.date_range(end=pd.Timestamp.now(), periods=len(out), freq="min")

    out = out.dropna(subset=["price"]).copy()
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out = out.dropna(subset=["time"]).sort_values("time").drop_duplicates(subset=["time"], keep="last")
    out["ret"] = out["price"].pct_change() * 100.0
    out["abs_ret"] = out["ret"].abs()
    return out.tail(5000)


def _window_change(frame, seconds):
    if frame.empty or len(frame) < 2:
        return 0.0, 0.0, "N/A"
    latest_time = frame["time"].iloc[-1]
    latest_price = _safe_num(frame["price"].iloc[-1])
    past = frame[frame["time"] <= latest_time - pd.Timedelta(seconds=seconds)]
    if past.empty:
        past_row = frame.iloc[0]
    else:
        past_row = past.iloc[-1]
    past_price = _safe_num(past_row["price"])
    elapsed = max((latest_time - past_row["time"]).total_seconds(), 1.0)
    change = latest_price - past_price
    pct = change / max(abs(past_price), 1e-9) * 100.0
    speed_per_sec = pct / elapsed
    return pct, speed_per_sec, str(past_row["time"])


def _directional_efficiency(prices):
    arr = pd.Series(prices).dropna().astype(float)
    if len(arr) < 3:
        return 0.0
    net = abs(arr.iloc[-1] - arr.iloc[0])
    path = arr.diff().abs().sum()
    return float(net / max(path, 1e-9) * 100.0)


def _trend_direction(prices):
    arr = pd.Series(prices).dropna().astype(float)
    if len(arr) < 2:
        return "FLAT"
    return "UP" if arr.iloc[-1] > arr.iloc[0] else "DOWN" if arr.iloc[-1] < arr.iloc[0] else "FLAT"


def _calc_market_analytics(df):
    frame = _prepare_market_frame(df)
    if frame.empty:
        return {}, pd.DataFrame()

    p_now = _safe_num(frame["price"].iloc[-1])
    sec10_pct, sec10_speed, sec10_time = _window_change(frame, 10)
    min1_pct, min1_speed, min1_time = _window_change(frame, 60)
    min10_pct, min10_speed, min10_time = _window_change(frame, 600)

    recent = frame.tail(11).copy()
    recent["bar_change_pct"] = recent["price"].pct_change() * 100.0
    biggest_row = recent.iloc[recent["bar_change_pct"].abs().fillna(0).argmax()] if len(recent) else frame.iloc[-1]

    last10 = frame.tail(10)
    prev10 = frame.tail(20).head(10) if len(frame) >= 20 else frame.head(max(1, len(frame) - 10))
    eff_now = _directional_efficiency(last10["price"])
    eff_prev = _directional_efficiency(prev10["price"])
    eff_change = eff_now - eff_prev
    eff_rising = max(0.0, eff_change)
    eff_falling = max(0.0, -eff_change)

    ret_window = frame["ret"].dropna().tail(120)
    ret_std = ret_window.std(ddof=0) if len(ret_window) else 0.0
    latest_ret = abs(_safe_num(frame["ret"].iloc[-1]))

    # Critical data-quality fix:
    # A displayed Fat Tail Z of 0 usually means either the latest candle did not move,
    # the feed is stale/duplicated, or there is not enough return dispersion yet.
    # We do NOT silently treat that as real fat-tail information. We mark it N/A for UI/copy output.
    fat_tail_available = bool(len(ret_window) >= 20 and np.isfinite(ret_std) and ret_std > 1e-12 and latest_ret > 1e-12)
    if fat_tail_available:
        fat_tail_z = latest_ret / max(ret_std, 1e-12)
        fat_tail_note = "OK: latest return compared against recent return dispersion."
    else:
        fat_tail_z = 0.0
        if len(ret_window) < 20:
            fat_tail_note = "N/A: not enough candles/returns for a reliable fat-tail reading."
        elif ret_std <= 1e-12:
            fat_tail_note = "N/A: recent returns have near-zero dispersion; feed may be stale or duplicated."
        else:
            fat_tail_note = "N/A: latest candle return is flat; do not interpret as zero tail risk."

    kurt = float(ret_window.kurt()) if len(ret_window) >= 20 and ret_std > 1e-12 else 0.0

    accel_abs = abs(sec10_speed - min1_speed) * 60.0
    direction = _trend_direction(last10["price"])

    fat_tail_for_score = fat_tail_z if fat_tail_available else 0.0
    one_way_score = min(100.0, max(0.0, eff_now * 0.65 + min(fat_tail_for_score, 4.0) * 8.0 + min(abs(min1_pct) * 20.0, 20.0)))
    trust = min(100.0, max(0.0, one_way_score - eff_falling * 0.7))

    if eff_now >= 75 and fat_tail_for_score >= 2.5 and eff_falling >= 8:
        regime = "ONE-WAY TREND REACHING LIMIT / EXHAUSTION RISK"
    elif eff_rising >= 8 and eff_now >= 55:
        regime = f"ONE-WAY TREND STARTING / CONTINUING {direction}"
    elif eff_now >= 70:
        regime = f"ONE-WAY TREND CONTINUES {direction}"
    elif eff_falling >= 12:
        regime = "ONE-WAY TREND STOPPING / CHOP RISK"
    elif fat_tail_for_score >= 3:
        regime = "IMPULSE / FAT-TAIL SHOCK"
    else:
        regime = "MIXED / ACCUMULATION OR NOISE"

    metrics = {
        "price_now": p_now,
        "sec10_pct": sec10_pct,
        "sec10_speed": sec10_speed,
        "min1_pct": min1_pct,
        "min1_speed": min1_speed,
        "min10_pct": min10_pct,
        "min10_speed": min10_speed,
        "accel_abs": accel_abs,
        "biggest_change_time": str(biggest_row.get("time", "N/A")),
        "biggest_change_pct": _safe_num(biggest_row.get("bar_change_pct")),
        "fat_tail_z": fat_tail_z,
        "fat_tail_available": fat_tail_available,
        "fat_tail_note": fat_tail_note,
        "kurtosis": kurt,
        "directional_efficiency": eff_now,
        "efficiency_prev": eff_prev,
        "efficiency_rising": eff_rising,
        "efficiency_falling": eff_falling,
        "trend_direction": direction,
        "one_way_score": one_way_score,
        "trust": trust,
        "regime": regime,
        "sec10_time": sec10_time,
        "min1_time": min1_time,
        "min10_time": min10_time,
    }
    return metrics, frame


def _record_account_live_snapshot(info):
    if not isinstance(info, dict) or not info:
        return pd.DataFrame()
    hist = st.session_state.get("doo_live_account_snapshots", [])
    now = pd.Timestamp.now()
    last = hist[-1]["time"] if hist else None
    try:
        enough_gap = last is None or (now - pd.to_datetime(last)).total_seconds() >= 1
    except Exception:
        enough_gap = True
    if enough_gap:
        hist.append({
            "time": now,
            "balance": _safe_num(info.get("balance")),
            "equity": _safe_num(info.get("equity")),
            "margin": _safe_num(info.get("margin")),
            "margin_free": _safe_num(info.get("margin_free")),
            "margin_level": _safe_num(info.get("margin_level")),
            "profit": _safe_num(info.get("profit")),
        })
    hist = hist[-7200:]
    st.session_state["doo_live_account_snapshots"] = hist
    return pd.DataFrame(hist)


def _margin_change_from_history(hist, seconds):
    if hist is None or hist.empty or "time" not in hist.columns or "margin_level" not in hist.columns:
        return 0.0
    df = hist.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["margin_level"] = pd.to_numeric(df["margin_level"], errors="coerce")
    df = df.dropna(subset=["time", "margin_level"]).sort_values("time")
    if len(df) < 2:
        return 0.0
    latest = df.iloc[-1]
    past = df[df["time"] <= latest["time"] - pd.Timedelta(seconds=seconds)]
    base = past.iloc[-1] if not past.empty else df.iloc[0]
    return _safe_num(latest["margin_level"]) - _safe_num(base["margin_level"])


def _margin_change_from_history_detail(hist, seconds):
    """Return (value, available, note). Avoid showing impossible zero before enough history exists."""
    if hist is None or hist.empty or "time" not in hist.columns or "margin_level" not in hist.columns:
        return 0.0, False, "N/A: no account snapshot history yet. Click/read account at least twice."
    df = hist.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["margin_level"] = pd.to_numeric(df["margin_level"], errors="coerce")
    df = df.dropna(subset=["time", "margin_level"]).sort_values("time")
    if len(df) < 2:
        return 0.0, False, "N/A: only one account snapshot. Need at least two snapshots."
    latest = df.iloc[-1]
    first = df.iloc[0]
    span = max((latest["time"] - first["time"]).total_seconds(), 0.0)
    if span < max(1, seconds * 0.80):
        return 0.0, False, f"N/A: history span is {round(span,1)}s; need about {seconds}s for this window."
    past = df[df["time"] <= latest["time"] - pd.Timedelta(seconds=seconds)]
    base = past.iloc[-1] if not past.empty else first
    value = _safe_num(latest["margin_level"]) - _safe_num(base["margin_level"])
    if abs(value) <= 1e-9:
        return 0.0, True, "Flat: margin level did not change during this measured window."
    return value, True, "OK: measured from real saved account snapshots."


def _pl_combination_table(positions_df):
    if positions_df is None or positions_df.empty or "profit" not in positions_df.columns:
        return pd.DataFrame(), {}
    df = positions_df.copy()
    if "side" not in df.columns:
        df["side"] = "UNKNOWN"
    df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0.0)
    buy_pl = float(df.loc[df["side"].astype(str).str.upper() == "BUY", "profit"].sum())
    sell_pl = float(df.loc[df["side"].astype(str).str.upper() == "SELL", "profit"].sum())
    profit_all = float(df.loc[df["profit"] > 0, "profit"].sum())
    loss_all = float(df.loc[df["profit"] < 0, "profit"].sum())
    net = float(df["profit"].sum())
    rows = [
        {"Combination": "BUY total P/L", "Value": round(buy_pl, 2), "Status": "GOOD" if buy_pl >= 0 else "BAD", "Meaning": "All BUY positions combined."},
        {"Combination": "SELL total P/L", "Value": round(sell_pl, 2), "Status": "GOOD" if sell_pl >= 0 else "BAD", "Meaning": "All SELL positions combined."},
        {"Combination": "All profit positions", "Value": round(profit_all, 2), "Status": "GOOD", "Meaning": "Only winning positions combined."},
        {"Combination": "All loss positions", "Value": round(loss_all, 2), "Status": "BAD" if loss_all < 0 else "GOOD", "Meaning": "Only losing positions combined."},
        {"Combination": "Net open P/L", "Value": round(net, 2), "Status": "GOOD" if net >= 0 else "BAD", "Meaning": "Profit and loss positions combined."},
    ]
    return pd.DataFrame(rows), {"buy_pl": buy_pl, "sell_pl": sell_pl, "profit_all": profit_all, "loss_all": loss_all, "net": net}



# ==========================================================
# EMERGENCY EXIT DECISION MATRIX
# ==========================================================


def _side_profit_stats(positions_df):
    """Summarize BUY/SELL baskets without sending or closing any trade."""
    empty = {
        "buy_pl": 0.0,
        "sell_pl": 0.0,
        "buy_lots": 0.0,
        "sell_lots": 0.0,
        "buy_count": 0,
        "sell_count": 0,
        "profit_all": 0.0,
        "loss_all": 0.0,
        "net_pl": 0.0,
        "buy_profit_count": 0,
        "sell_profit_count": 0,
        "buy_profit_pct": 0.0,
        "sell_profit_pct": 0.0,
    }
    if positions_df is None or positions_df.empty:
        return empty

    df = positions_df.copy()
    if "side" not in df.columns:
        df["side"] = "UNKNOWN"
    for col in ["profit", "volume", "swap", "price_open", "price_current"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    side = df["side"].astype(str).str.upper()
    profit = pd.to_numeric(df.get("profit", 0.0), errors="coerce").fillna(0.0)
    volume = pd.to_numeric(df.get("volume", 0.0), errors="coerce").fillna(0.0)

    out = dict(empty)
    out["buy_pl"] = float(profit[side == "BUY"].sum())
    out["sell_pl"] = float(profit[side == "SELL"].sum())
    out["buy_lots"] = float(volume[side == "BUY"].sum())
    out["sell_lots"] = float(volume[side == "SELL"].sum())
    out["buy_count"] = int((side == "BUY").sum())
    out["sell_count"] = int((side == "SELL").sum())
    out["buy_profit_count"] = int(((side == "BUY") & (profit > 0)).sum())
    out["sell_profit_count"] = int(((side == "SELL") & (profit > 0)).sum())
    out["buy_profit_pct"] = out["buy_profit_count"] / max(out["buy_count"], 1) * 100.0
    out["sell_profit_pct"] = out["sell_profit_count"] / max(out["sell_count"], 1) * 100.0
    out["profit_all"] = float(profit[profit > 0].sum())
    out["loss_all"] = float(profit[profit < 0].sum())
    out["net_pl"] = float(profit.sum())
    return out


def _infer_contract_value_per_lot(positions_df):
    """Infer money change per +1.00 price move per 1.00 lot from live positions.

    For XAUUSD cent-style accounts this is often near 100, but this function learns it from
    the real open-position profit/open/current prices so it is safer across symbols/brokers.
    """
    if positions_df is None or positions_df.empty:
        return 100.0

    vals = []
    for _, row in positions_df.iterrows():
        side = str(row.get("side", "")).upper()
        vol = _safe_num(row.get("volume"))
        po = _safe_num(row.get("price_open"))
        pc = _safe_num(row.get("price_current"))
        profit = _safe_num(row.get("profit")) - _safe_num(row.get("swap")) - _safe_num(row.get("commission"))
        if vol <= 0 or po <= 0 or pc <= 0 or side not in ["BUY", "SELL"]:
            continue
        signed_move = (pc - po) if side == "BUY" else (po - pc)
        if abs(signed_move) <= 1e-9:
            continue
        v = profit / (signed_move * vol)
        if np.isfinite(v) and 0 < abs(v) < 1_000_000:
            vals.append(abs(float(v)))

    if vals:
        try:
            return float(np.nanmedian(vals))
        except Exception:
            return float(vals[len(vals) // 2])

    symbols = " ".join([str(x).upper() for x in positions_df.get("symbol", pd.Series(dtype=str)).unique().tolist()])
    if "XAU" in symbols or "GOLD" in symbols:
        return 100.0
    if "XAG" in symbols or "SILVER" in symbols:
        return 50.0
    return 100000.0 if any(x in symbols for x in ["EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"]) else 100.0


def _margin_split_by_side(info, positions_df, stats=None):
    """Estimate margin carried by BUY and SELL baskets.

    MT5 account_info gives total account margin, not always per-position margin. If position-level
    margin exists, use it. Otherwise split total margin by lots, which is safer than pretending the
    margin after a basket close is unknown.
    """
    stats = stats or _side_profit_stats(positions_df)
    total_margin = _safe_num((info or {}).get("margin"))
    if positions_df is None or positions_df.empty or total_margin <= 0:
        return 0.0, 0.0

    df = positions_df.copy()
    if "side" not in df.columns:
        df["side"] = "UNKNOWN"
    side = df["side"].astype(str).str.upper()

    for candidate in ["margin", "position_margin", "margin_initial", "margin_maintenance"]:
        if candidate in df.columns:
            m = pd.to_numeric(df[candidate], errors="coerce").fillna(0.0)
            if float(m.abs().sum()) > 0:
                return float(m[side == "BUY"].sum()), float(m[side == "SELL"].sum())

    buy_lots = max(_safe_num(stats.get("buy_lots")), 0.0)
    sell_lots = max(_safe_num(stats.get("sell_lots")), 0.0)
    total_lots = max(buy_lots + sell_lots, 1e-9)
    return total_margin * buy_lots / total_lots, total_margin * sell_lots / total_lots


def _safe_stopout_level(info):
    so = _safe_num((info or {}).get("margin_so_so"), 30.0)
    if so <= 0:
        so = 30.0
    return float(so)


def _safe_call_level(info):
    call = _safe_num((info or {}).get("margin_so_call"), 100.0)
    if call <= 0:
        call = 100.0
    return float(call)


def _market_direction_score(market, q):
    """Return positive score for UP/BUY pressure and DOWN/SELL pressure."""
    market = market or {}
    q = q or {}
    up = 0.0
    down = 0.0

    direction = str(market.get("trend_direction", "")).upper()
    if direction in ["UP", "BUY", "BULL"]:
        up += 2.0
    elif direction in ["DOWN", "SELL", "BEAR"]:
        down += 2.0

    q_bias = str(q.get("bias", "")).upper()
    q_safe = _safe_num(q.get("safe_pct"))
    if q_bias == "BUY":
        up += 1.5 + max(0.0, min(q_safe, 100.0) - 50.0) / 25.0
    elif q_bias == "SELL":
        down += 1.5 + max(0.0, min(q_safe, 100.0) - 50.0) / 25.0

    for key, weight in [("sec10_pct", 0.5), ("min1_pct", 0.8), ("min10_pct", 1.0)]:
        v = _safe_num(market.get(key))
        if v > 0:
            up += min(abs(v) * 20.0, 1.0) * weight
        elif v < 0:
            down += min(abs(v) * 20.0, 1.0) * weight

    pressure = _safe_num(q.get("pressure", (q.get("regime_meta", {}) or {}).get("pressure", 0.0)))
    if pressure > 0:
        up += min(abs(pressure) / 20.0, 1.5)
    elif pressure < 0:
        down += min(abs(pressure) / 20.0, 1.5)

    trend_note = "MIXED"
    if up >= down + 1.5:
        trend_note = "UP / BUY PRESSURE"
    elif down >= up + 1.5:
        trend_note = "DOWN / SELL PRESSURE"
    return {"up_score": round(up, 2), "down_score": round(down, 2), "direction_note": trend_note}


def _points_label(v):
    try:
        if v is None or not np.isfinite(float(v)):
            return "∞ / hedged"
        return round(float(v), 2)
    except Exception:
        return "N/A"


def _simulate_exit_scenarios(info, positions_df, market=None, q=None):
    """Simulate HOLD vs close full BUY vs close full SELL.

    This does not execute trades. It estimates what remains after closing a basket and how many
    price points the remaining one-way exposure can move against the account before the stop-out
    proxy is reached.
    """
    if not isinstance(info, dict) or not info:
        return {}, pd.DataFrame()
    if positions_df is None or positions_df.empty:
        return {}, pd.DataFrame()

    stats = _side_profit_stats(positions_df)
    buy_margin, sell_margin = _margin_split_by_side(info, positions_df, stats)
    contract = _infer_contract_value_per_lot(positions_df)
    equity = _safe_num(info.get("equity"), _safe_num(info.get("balance")))
    total_margin = _safe_num(info.get("margin"))
    current_margin_level = _safe_num(info.get("margin_level"), equity / max(total_margin, 1e-9) * 100.0 if total_margin else 0.0)
    stopout = _safe_stopout_level(info)
    call = _safe_call_level(info)
    mscore = _market_direction_score(market, q)

    buy_lots = _safe_num(stats.get("buy_lots"))
    sell_lots = _safe_num(stats.get("sell_lots"))

    specs = [
        {
            "scenario": "HOLD BOTH SIDES",
            "close_side": "HOLD",
            "remaining": "BUY + SELL hedge",
            "remaining_lots": buy_lots + sell_lots,
            "remaining_margin": total_margin,
            "delta_per_up_point": contract * (buy_lots - sell_lots),
            "realized_pl_if_closed": 0.0,
            "closed_margin_est": 0.0,
        },
        {
            "scenario": "EXIT ALL BUY NOW",
            "close_side": "BUY",
            "remaining": "SELL only",
            "remaining_lots": sell_lots,
            "remaining_margin": sell_margin,
            "delta_per_up_point": -contract * sell_lots,
            "realized_pl_if_closed": _safe_num(stats.get("buy_pl")),
            "closed_margin_est": buy_margin,
        },
        {
            "scenario": "EXIT ALL SELL NOW",
            "close_side": "SELL",
            "remaining": "BUY only",
            "remaining_lots": buy_lots,
            "remaining_margin": buy_margin,
            "delta_per_up_point": contract * buy_lots,
            "realized_pl_if_closed": _safe_num(stats.get("sell_pl")),
            "closed_margin_est": sell_margin,
        },
    ]

    rows = []
    for spec in specs:
        rem_margin = max(_safe_num(spec.get("remaining_margin")), 0.0)
        delta_up = _safe_num(spec.get("delta_per_up_point"))
        if rem_margin <= 0:
            margin_after = 9999.0
            buffer_so = equity
            buffer_call = equity
        else:
            margin_after = equity / max(rem_margin, 1e-9) * 100.0
            buffer_so = equity - rem_margin * stopout / 100.0
            buffer_call = equity - rem_margin * call / 100.0

        if abs(delta_up) <= 1e-9:
            danger_direction = "Mostly hedged"
            loss_per_point = 0.0
            points_to_so = float("inf")
            points_to_call = float("inf")
        elif delta_up > 0:
            danger_direction = "Price DOWN hurts remaining basket"
            loss_per_point = abs(delta_up)
            points_to_so = buffer_so / loss_per_point if buffer_so > 0 else 0.0
            points_to_call = buffer_call / loss_per_point if buffer_call > 0 else 0.0
        else:
            danger_direction = "Price UP hurts remaining basket"
            loss_per_point = abs(delta_up)
            points_to_so = buffer_so / loss_per_point if buffer_so > 0 else 0.0
            points_to_call = buffer_call / loss_per_point if buffer_call > 0 else 0.0

        market_alignment = "NEUTRAL"
        if "UP" in danger_direction and mscore["up_score"] >= mscore["down_score"] + 1.5:
            market_alignment = "DANGEROUS: market pressure is against remaining SELL"
        elif "DOWN" in danger_direction and mscore["down_score"] >= mscore["up_score"] + 1.5:
            market_alignment = "DANGEROUS: market pressure is against remaining BUY"
        elif "UP" in danger_direction and mscore["down_score"] >= mscore["up_score"] + 1.5:
            market_alignment = "FAVOURABLE: remaining SELL follows pressure"
        elif "DOWN" in danger_direction and mscore["up_score"] >= mscore["down_score"] + 1.5:
            market_alignment = "FAVOURABLE: remaining BUY follows pressure"

        rows.append({
            "Scenario": spec["scenario"],
            "Close Side": spec["close_side"],
            "Remaining Basket": spec["remaining"],
            "Remaining Lots": round(_safe_num(spec.get("remaining_lots")), 3),
            "Estimated Margin After": round(rem_margin, 2),
            "Margin Level After %": round(margin_after, 2),
            "Stop-Out Buffer": round(buffer_so, 2),
            "Danger Direction": danger_direction,
            "Loss / Price Point": round(loss_per_point, 2),
            "Points To Stop-Out": _points_label(points_to_so),
            "Points To Margin Call": _points_label(points_to_call),
            "Realized P/L If Closed": round(_safe_num(spec.get("realized_pl_if_closed")), 2),
            "Closed Margin Est.": round(_safe_num(spec.get("closed_margin_est")), 2),
            "Market Alignment": market_alignment,
        })

    overview = {
        "equity": equity,
        "current_margin": total_margin,
        "current_margin_level": current_margin_level,
        "stopout_level": stopout,
        "call_level": call,
        "danger_gap_pct": current_margin_level - stopout,
        "contract_value_per_lot": contract,
        "market_score": mscore,
        "stats": stats,
    }
    return overview, pd.DataFrame(rows)


def _choose_emergency_action(overview, scenarios):
    if not overview or scenarios is None or scenarios.empty:
        return {
            "action": "READ DATA FIRST",
            "action_short": "READ DATA",
            "confidence": "LOW",
            "reason": "No account/position data available.",
        }

    gap = _safe_num(overview.get("danger_gap_pct"))
    mscore = overview.get("market_score", {}) or {}
    up_score = _safe_num(mscore.get("up_score"))
    down_score = _safe_num(mscore.get("down_score"))

    def pts_for(name):
        row = scenarios.loc[scenarios["Scenario"] == name]
        if row.empty:
            return 0.0
        v = row.iloc[0].get("Points To Stop-Out")
        try:
            if isinstance(v, str) and "∞" in v:
                return float("inf")
            return float(v)
        except Exception:
            return 0.0

    hold_pts = pts_for("HOLD BOTH SIDES")
    close_buy_pts = pts_for("EXIT ALL BUY NOW")
    close_sell_pts = pts_for("EXIT ALL SELL NOW")
    stats = overview.get("stats", {}) or {}
    buy_profit_pct = _safe_num(stats.get("buy_profit_pct"))
    sell_profit_pct = _safe_num(stats.get("sell_profit_pct"))
    buy_pl = _safe_num(stats.get("buy_pl"))
    sell_pl = _safe_num(stats.get("sell_pl"))
    buy_gate_ok = buy_profit_pct >= 40.0 or buy_pl >= 0.0
    sell_gate_ok = sell_profit_pct >= 40.0 or sell_pl >= 0.0

    # If a full side close creates a one-way basket with very small stop-out room, do not recommend it.
    one_side_min = min(close_buy_pts if np.isfinite(close_buy_pts) else 999999, close_sell_pts if np.isfinite(close_sell_pts) else 999999)
    full_side_too_dangerous = one_side_min < 25 and hold_pts > one_side_min * 2

    if gap <= 5:
        return {
            "action": "URGENT: REDUCE BOTH SIDES / ADD MARGIN BUFFER",
            "action_short": "URGENT BOTH",
            "confidence": "HIGH",
            "reason": "Margin level is very close to broker stop-out. Avoid opening new trades; reduce exposure in paired BUY+SELL lots or add margin if that is your plan.",
        }

    if full_side_too_dangerous:
        return {
            "action": "HOLD FULL-SIDE EXIT; REDUCE PAIRED BUY+SELL ONLY",
            "action_short": "HOLD/PAIR",
            "confidence": "HIGH",
            "reason": "Closing all BUY or all SELL leaves a one-way basket with small price-room to stop-out. Paired reduction lowers margin without creating a naked one-way basket.",
        }

    if up_score >= down_score + 2 and close_sell_pts >= max(25, close_buy_pts * 1.25):
        if sell_gate_ok:
            return {"action": "EXIT / REDUCE SELL FIRST", "action_short": "EXIT SELL", "confidence": "MEDIUM", "reason": f"Market pressure is UP/BUY and SELL basket P/L gate is acceptable: {sell_profit_pct:.1f}% profitable, SELL P/L={sell_pl:.2f}."}
        return {"action": "EXIT SELL WATCH ONLY; WAIT FOR SELL BASKET RECOVERY OR USE PAIRED REDUCTION", "action_short": "SELL WATCH", "confidence": "LOW", "reason": f"UP/BUY pressure exists, but SELL basket is mostly negative: only {sell_profit_pct:.1f}% profitable and SELL P/L={sell_pl:.2f}."}

    if down_score >= up_score + 2 and close_buy_pts >= max(25, close_sell_pts * 1.25):
        if buy_gate_ok:
            return {"action": "EXIT / REDUCE BUY FIRST", "action_short": "EXIT BUY", "confidence": "MEDIUM", "reason": f"Market pressure is DOWN/SELL and BUY basket P/L gate is acceptable: {buy_profit_pct:.1f}% profitable, BUY P/L={buy_pl:.2f}."}
        return {"action": "EXIT BUY WATCH ONLY; WAIT FOR BUY BASKET RECOVERY OR USE PAIRED REDUCTION", "action_short": "BUY WATCH", "confidence": "LOW", "reason": f"DOWN/SELL pressure exists, but BUY basket is mostly negative: only {buy_profit_pct:.1f}% profitable and BUY P/L={buy_pl:.2f}."}

    if gap <= 20:
        return {
            "action": "DANGER HOLD; REDUCE PAIRED LOTS BEFORE ONE-SIDE EXIT",
            "action_short": "DANGER HOLD",
            "confidence": "MEDIUM",
            "reason": "Margin level is still dangerous. Full one-side exit needs cleaner market confirmation and larger stop-out room.",
        }

    return {
        "action": "HOLD UNTIL CLEAR BREAK; PLAN PAIRED REDUCTION",
        "action_short": "HOLD",
        "confidence": "MEDIUM",
        "reason": "No full-side exit has a clearly superior survival profile yet.",
    }


def _build_emergency_exit_decision(info, positions_df, market=None, q=None):
    if q is None:
        try:
            df = st.session_state.get("last_df")
            q = _safe_quant_stack(df) if isinstance(df, pd.DataFrame) and not df.empty else {}
        except Exception:
            q = {}
    if market is None:
        try:
            market, _ = _calc_market_analytics(st.session_state.get("last_df"))
        except Exception:
            market = {}

    overview, scenarios = _simulate_exit_scenarios(info, positions_df, market, q)
    action = _choose_emergency_action(overview, scenarios)
    action["overview"] = overview
    action["scenario_rows"] = scenarios.to_dict(orient="records") if isinstance(scenarios, pd.DataFrame) else []
    return action, scenarios


def _paired_reduction_candidates(positions_df, total_margin=0.0, max_rows=8):
    """Find BUY+SELL pairs that reduce margin while keeping the hedge direction balanced."""
    if positions_df is None or positions_df.empty:
        return pd.DataFrame()
    df = positions_df.copy()
    if "side" not in df.columns:
        return pd.DataFrame()
    for col in ["profit", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    buys = df[df["side"].astype(str).str.upper() == "BUY"].sort_values("profit", ascending=False).reset_index(drop=True)
    sells = df[df["side"].astype(str).str.upper() == "SELL"].sort_values("profit", ascending=False).reset_index(drop=True)
    if buys.empty or sells.empty:
        return pd.DataFrame()

    total_lots = float(pd.to_numeric(df.get("volume", 0.0), errors="coerce").fillna(0.0).sum())
    margin_per_lot = _safe_num(total_margin) / max(total_lots, 1e-9)
    rows = []
    n = min(len(buys), len(sells), int(max_rows))
    for i in range(n):
        b = buys.iloc[i]
        s = sells.iloc[i]
        bv = _safe_num(b.get("volume"))
        sv = _safe_num(s.get("volume"))
        pair_lots = min(bv, sv)
        combined_pl = _safe_num(b.get("profit")) + _safe_num(s.get("profit"))
        rows.append({
            "Rank": i + 1,
            "BUY Ticket": b.get("ticket", ""),
            "BUY Lot": round(bv, 3),
            "BUY P/L": round(_safe_num(b.get("profit")), 2),
            "SELL Ticket": s.get("ticket", ""),
            "SELL Lot": round(sv, 3),
            "SELL P/L": round(_safe_num(s.get("profit")), 2),
            "Matched Lot": round(pair_lots, 3),
            "Combined P/L": round(combined_pl, 2),
            "Approx Margin Freed": round(margin_per_lot * (bv + sv), 2) if margin_per_lot > 0 else 0.0,
            "Meaning": "Closes one BUY and one SELL together so net direction changes less than closing one full side.",
        })
    return pd.DataFrame(rows)


def _render_emergency_exit_decision(info, positions_df, market=None, q=None, expanded=True):
    st.markdown("##### 🚨 Tomorrow Emergency Exit Decision Matrix")
    st.caption(
        "This dashboard does not execute orders. It estimates which action creates the least stop-out danger: "
        "hold, exit BUY, exit SELL, or reduce both sides in paired lots. Use it as a risk-control panel, not a guaranteed prediction."
    )

    if not isinstance(info, dict) or not info:
        st.info("Read the real Doo Prime/MT5 account snapshot first. Market-only data cannot decide which open basket to exit.")
        return
    if positions_df is None or positions_df.empty:
        st.info("No open positions found, so there is no BUY/SELL exit basket to compare.")
        return

    action, scenarios = _build_emergency_exit_decision(info, positions_df, market, q)
    overview = action.get("overview", {}) or {}
    stats = overview.get("stats", {}) or {}
    mscore = overview.get("market_score", {}) or {}

    cols = st.columns(7)
    cols[0].metric("Recommended Action", action.get("action_short", "READ"))
    cols[0].caption(f"{action.get('confidence', 'LOW')} confidence: {action.get('reason', '')}")
    cols[1].metric("Margin Level %", round(_safe_num(overview.get("current_margin_level")), 2))
    cols[1].caption(f"Stop-out: {round(_safe_num(overview.get('stopout_level')), 2)}%")
    cols[2].metric("Danger Gap %", round(_safe_num(overview.get("danger_gap_pct")), 2))
    cols[2].caption("Margin level minus stop-out level.")

    def scenario_metric(name, col, label):
        row = scenarios.loc[scenarios["Scenario"] == name] if isinstance(scenarios, pd.DataFrame) and not scenarios.empty else pd.DataFrame()
        if row.empty:
            col.metric(label, "N/A")
            return
        r = row.iloc[0]
        col.metric(label, r.get("Points To Stop-Out", "N/A"))
        col.caption(str(r.get("Danger Direction", ""))[:95])

    scenario_metric("HOLD BOTH SIDES", cols[3], "Hold Stop-Out Room")
    scenario_metric("EXIT ALL BUY NOW", cols[4], "Exit BUY → SELL Room")
    scenario_metric("EXIT ALL SELL NOW", cols[5], "Exit SELL → BUY Room")
    cols[6].metric("Market Pressure", mscore.get("direction_note", "MIXED"))
    cols[6].caption(f"UP {mscore.get('up_score', 0)} / DOWN {mscore.get('down_score', 0)}")

    if action.get("action_short") in ["HOLD/PAIR", "DANGER HOLD", "URGENT BOTH"]:
        st.warning(action.get("action", "HOLD / paired reduction preferred."))
    elif "SELL" in action.get("action_short", "") or "BUY" in action.get("action_short", ""):
        st.success(action.get("action", "Directional reduction preferred."))
    else:
        st.info(action.get("action", "Hold until cleaner confirmation."))

    with st.expander("📋 Open exit scenario table", expanded=False):
        st.dataframe(scenarios, use_container_width=True, hide_index=True)

    st.markdown("###### Basket P/L and Lot Balance")
    bcols = st.columns(6)
    bcols[0].metric("BUY P/L", round(_safe_num(stats.get("buy_pl")), 2))
    bcols[1].metric("SELL P/L", round(_safe_num(stats.get("sell_pl")), 2))
    bcols[2].metric("BUY Lots", round(_safe_num(stats.get("buy_lots")), 3))
    bcols[3].metric("SELL Lots", round(_safe_num(stats.get("sell_lots")), 3))
    bcols[4].metric("Net Lots", round(_safe_num(stats.get("buy_lots")) - _safe_num(stats.get("sell_lots")), 3))
    bcols[5].metric("Contract/Lot Est.", round(_safe_num(overview.get("contract_value_per_lot")), 2))

    pair_df = _paired_reduction_candidates(positions_df, _safe_num(overview.get("current_margin")), max_rows=8)
    if not pair_df.empty:
        with st.expander("Paired reduction candidates: lower margin without becoming one-way", expanded=expanded):
            st.write(
                "When full BUY or full SELL exit is dangerous, reduce one BUY and one SELL together. "
                "Prefer positive combined P/L pairs first; if none exist, use the smallest-loss pair needed to free margin."
            )
            st.dataframe(pair_df, use_container_width=True, hide_index=True)

    st.markdown("###### Practical rule for tomorrow")
    st.write(
        "1) If **Exit BUY → remaining SELL room** or **Exit SELL → remaining BUY room** is small, do not close that full side at once. "
        "2) If market pressure is UP, the SELL basket is the side that can blow the account faster; if pressure is DOWN, the BUY basket is the side that can blow faster. "
        "3) When margin level is already under 80%, the safer emergency method is usually **paired reduction** until margin level is far above the broker stop-out zone."
    )

def _show_advanced_doo_analytics(info, positions_df):
    st.markdown("#### ⚡ Advanced Live Doo Prime Analytics")
    st.caption("Uses your connected market dataframe plus real account snapshot. It is analytical guidance, not a guaranteed prediction.")

    hist = _record_account_live_snapshot(info)
    # Prefer the dedicated Doo Prime MT5 candle cache. If it is empty, fall back
    # to the sidebar/shared dataframe so old behavior still works.
    df = st.session_state.get("doo_prime_market_df")
    if df is None or getattr(df, "empty", True):
        df = st.session_state.get("last_df")
    market, market_frame = _calc_market_analytics(df)
    try:
        q_for_exit = _safe_quant_stack(df) if isinstance(df, pd.DataFrame) and not df.empty else {}
    except Exception:
        q_for_exit = {}

    _render_emergency_exit_decision(info, positions_df, market, q_for_exit, expanded=False)

    if not market:
        st.info("Connect Doo Prime MT5 Account, or connect sidebar market data, to calculate price speed, derivative, fat-tail, and directional efficiency.")
    else:
        st.markdown("##### Price Change Speed + Derivative")
        r1 = st.columns(6)
        s1, n1 = _analytics_status("price_speed_abs_pct_min", abs(market["sec10_speed"] * 60.0))
        s2, n2 = _analytics_status("price_speed_abs_pct_min", abs(market["min1_speed"] * 60.0))
        s3, n3 = _analytics_status("price_accel_abs", market["accel_abs"])
        r1[0].metric("Current Price", round(market["price_now"], 5))
        r1[0].caption("Latest connected close/bid price.")
        r1[1].metric("10s Change %", round(market["sec10_pct"], 4))
        r1[1].caption(f"{_status_badge(s1)} {s1}: {n1}")
        r1[2].metric("1m Change %", round(market["min1_pct"], 4))
        r1[2].caption(f"{_status_badge(s2)} {s2}: {n2}")
        r1[3].metric("10m Change %", round(market["min10_pct"], 4))
        r1[3].caption("Bigger context movement.")
        r1[4].metric("Derivative / Accel", round(market["accel_abs"], 4))
        r1[4].caption(f"{_status_badge(s3)} {s3}: {n3}")
        r1[5].metric("Most Change Time", market["biggest_change_time"][-19:])
        r1[5].caption(f"Biggest recent bar: {round(market['biggest_change_pct'], 4)}%")

        st.markdown("##### Fat Tail + Directional Volatility Efficiency")
        r2 = st.columns(6)
        fs, fn = _analytics_status("fat_tail_z", market["fat_tail_z"])
        es, en = _analytics_status("directional_efficiency", market["directional_efficiency"])
        rs, rn = _analytics_status("efficiency_rising", market["efficiency_rising"])
        ls, ln = _analytics_status("efficiency_falling", market["efficiency_falling"])
        fat_tail_label = round(market["fat_tail_z"], 2) if market.get("fat_tail_available", False) else "N/A"
        r2[0].metric("Fat Tail Z", fat_tail_label)
        if market.get("fat_tail_available", False):
            r2[0].caption(f"{_status_badge(fs)} {fs}: {fn}")
        else:
            r2[0].caption(f"⚪ DATA CHECK: {market.get('fat_tail_note', 'Fat-tail is not reliable yet.')}")
        r2[1].metric("Kurtosis", round(market["kurtosis"], 2))
        r2[1].caption("Higher means returns have heavier tails and more shock risk.")
        r2[2].metric("Directional Efficiency %", round(market["directional_efficiency"], 2))
        r2[2].caption(f"{_status_badge(es)} {es}: {en}")
        r2[3].metric("Rising Efficiency %", round(market["efficiency_rising"], 2))
        r2[3].caption(f"{_status_badge(rs)} {rs}: {rn}")
        r2[4].metric("Falling Efficiency %", round(market["efficiency_falling"], 2))
        r2[4].caption(f"{_status_badge(ls)} {ls}: {ln}")
        r2[5].metric("Trust Scale", f"{round(market['trust'], 1)}%")
        r2[5].caption(f"One-way score: {round(market['one_way_score'], 1)}%")

        if "STARTING" in market["regime"] or "CONTINUING" in market["regime"]:
            st.success(f"✅ Important: {market['regime']} | Direction: {market['trend_direction']} | Trust: {round(market['trust'], 1)}%")
        elif "LIMIT" in market["regime"] or "EXHAUSTION" in market["regime"] or "STOPPING" in market["regime"]:
            st.warning(f"⚠️ Important: {market['regime']} | Direction: {market['trend_direction']} | Trust: {round(market['trust'], 1)}%")
        elif "SHOCK" in market["regime"]:
            st.error(f"🚨 Important: {market['regime']} | Fat-tail value is high. Avoid blind chasing.")
        else:
            st.info(f"Market Regime: {market['regime']} | Direction: {market['trend_direction']}")

        explain = pd.DataFrame([
            {"Data": "Fat Tail Z", "Current": round(market["fat_tail_z"], 2) if market.get("fat_tail_available", False) else "N/A", "Meaning": "How unusual the latest move is versus recent returns. Above 2 is important; above 3 is extreme. N/A means stale/flat/insufficient feed, not zero risk."},
            {"Data": "Directional Efficiency", "Current": round(market["directional_efficiency"], 2), "Meaning": "Net direction divided by total path. High value means cleaner one-way trend."},
            {"Data": "Rising Efficiency", "Current": round(market["efficiency_rising"], 2), "Meaning": "Positive increase means trend quality is improving and one-way movement may be starting."},
            {"Data": "Falling Efficiency", "Current": round(market["efficiency_falling"], 2), "Meaning": "Positive value means one-way trend quality is decaying; trend may be near limit or stopping."},
            {"Data": "Derivative / Acceleration", "Current": round(market["accel_abs"], 4), "Meaning": "Difference between short speed and minute speed. High value means price movement is accelerating."},
        ])
        with st.expander("📘 Open analytics meaning table", expanded=False):
            st.dataframe(explain, use_container_width=True, hide_index=True)

    st.markdown("##### P/L Buy, Sell, Profit/Loss Combination")
    combo_df, combo = _pl_combination_table(positions_df)
    if combo_df.empty:
        st.info("No open positions available for P/L combination analysis.")
    else:
        c = st.columns(5)
        c[0].metric("BUY P/L", round(combo.get("buy_pl", 0), 2))
        c[0].caption("GOOD if BUY basket is positive; BAD if negative.")
        c[1].metric("SELL P/L", round(combo.get("sell_pl", 0), 2))
        c[1].caption("GOOD if SELL basket is positive; BAD if negative.")
        c[2].metric("All Profit", round(combo.get("profit_all", 0), 2))
        c[2].caption("Sum of all winning positions.")
        c[3].metric("All Loss", round(combo.get("loss_all", 0), 2))
        c[3].caption("Sum of all losing positions.")
        c[4].metric("Net P/L", round(combo.get("net", 0), 2))
        c[4].caption("Total open floating result.")
        with st.expander("💰 Open P/L combination table", expanded=False):
            st.dataframe(combo_df, use_container_width=True, hide_index=True)

    st.markdown("##### Margin Level Change Speed")
    margin_windows = [("Per Second", 1), ("Per Minute", 60), ("Per Hour", 3600)]
    mr = st.columns(3)
    for col, (label, seconds) in zip(mr, margin_windows):
        val, available, data_note = _margin_change_from_history_detail(hist, seconds)
        ms, mn = _analytics_status("margin_level_change", val)
        col.metric(f"Margin Level Change {label}", round(val, 4) if available else "N/A")
        if available:
            col.caption(f"{_status_badge(ms)} {ms}: {mn} | {data_note}")
        else:
            col.caption(f"⚪ DATA CHECK: {data_note}")

    if hist is not None and not hist.empty and len(hist) >= 2:
        chart = hist.copy()
        chart["time"] = pd.to_datetime(chart["time"], errors="coerce")
        chart = chart.dropna(subset=["time"]).set_index("time")
        show_cols = [x for x in ["margin_level", "equity", "profit"] if x in chart.columns]
        if show_cols:
            st.line_chart(chart[show_cols].tail(300))


# ==========================================================
# DOO PRIME ACCOUNT PANEL
# ==========================================================


def _doo_prime_connect_mt5_account_and_market():
    """Dedicated Doo Prime / MetaTrader connector.

    This is intentionally separate from the sidebar API selector.  The sidebar can
    stay on TwelveData/fallback for general candles, while the Doo Prime Account
    button reads the real local MT5 account and optionally caches MT5 candles for
    Doo analysis without fighting the sidebar connector mode.
    """
    symbol = str(st.session_state.get("symbol", "XAUUSD") or "XAUUSD").strip().upper()
    timeframe = str(st.session_state.get("doo_prime_mt5_timeframe", st.session_state.get("timeframe", "M1")) or "M1").upper()
    bars = int(st.session_state.get("doo_prime_mt5_bars", min(int(st.session_state.get("connector_bars", 600) or 600), 5000)) or 600)

    info, acct_ok, acct_msg = _safe_mt5_account_info()
    if isinstance(info, dict) and info:
        st.session_state.account_snapshot = info
        st.session_state.doo_prime_account_snapshot = info
        st.session_state.doo_prime_account_connected = bool(acct_ok)
        st.session_state.doo_prime_account_last_read = pd.Timestamp.now().isoformat()

    market_ok = False
    market_msg = "MT5 candle reader unavailable."
    if fetch_mt5 is not None:
        try:
            df, market_ok, market_msg = fetch_mt5(symbol=symbol, timeframe=timeframe, bars=bars)
            if market_ok and df is not None and not getattr(df, "empty", True):
                st.session_state.doo_prime_market_df = df
                st.session_state.doo_prime_market_source = "MT5"
                st.session_state.doo_prime_market_symbol = symbol
                st.session_state.doo_prime_market_timeframe = timeframe
                st.session_state.doo_prime_market_rows = len(df)
                st.session_state.doo_prime_market_last_fetch = time.time()
                # Share MT5 candles only when the global connector is disconnected or the user allows sync.
                if (not st.session_state.get("connected")) or bool(st.session_state.get("doo_prime_sync_to_shared", False)):
                    st.session_state.last_df = df
                    st.session_state.connected = True
                    st.session_state.source = "MT5"
                    st.session_state.last_fetch = time.time()
                    st.session_state.last_connection_message = "Doo Prime MT5 synced to shared dataframe"
        except Exception as exc:
            market_ok = False
            market_msg = f"MT5 market read failed: {exc}"

    st.session_state.doo_prime_last_connect_status = {
        "account_ok": bool(acct_ok),
        "market_ok": bool(market_ok),
        "account_message": str(acct_msg),
        "market_message": str(market_msg),
        "time": pd.Timestamp.now().isoformat(),
    }
    return bool(acct_ok), str(acct_msg), bool(market_ok), str(market_msg)


def doo_prime_account_panel():
    st.markdown("### 🏦 Doo Prime / MT5 Account Reader")

    st.caption(
        "Dedicated Doo Prime/MetaTrader channel: this Account button reads local MT5 account + optional MT5 candles. "
        "The sidebar API connector can stay on TwelveData/fallback without conflict."
    )

    with st.expander("⚙️ Tiny Doo MT5 link options", expanded=False):
        ctf, cbars, csync = st.columns(3)
        with ctf:
            st.selectbox("MT5 TF", ["M1", "M2", "M5", "M15", "M30", "H1"], key="doo_prime_mt5_timeframe")
        with cbars:
            st.number_input("MT5 bars", 100, 20000, int(st.session_state.get("doo_prime_mt5_bars", 600) or 600), 100, key="doo_prime_mt5_bars")
        with csync:
            st.checkbox("Sync to shared df", value=bool(st.session_state.get("doo_prime_sync_to_shared", False)), key="doo_prime_sync_to_shared", help="OFF keeps sidebar API separate. ON lets Doo Prime MT5 feed all tabs.")
        status = st.session_state.get("doo_prime_last_connect_status", {})
        if status:
            st.caption(f"Doo link: account={status.get('account_ok')} | market={status.get('market_ok')} | {status.get('time','')}")

    compact_mode = bool(st.session_state.get("doo_prime_compact_controls", False))

    # Always show the real Doo Prime account reader inside the Account tab.
    # Earlier compact mode hid this button and made the user think Account only meant
    # the sidebar market connector.  This restores the original account-read workflow
    # while keeping the upgraded compact navigation.
    c0, c1, c2 = st.columns(3)

    with c0:
        if st.button("🔌 Connect Doo Prime MT5 Account", use_container_width=True, key="home_doo_read"):
            acct_ok, acct_msg, market_ok, market_msg = _doo_prime_connect_mt5_account_and_market()
            if acct_ok:
                st.success(f"Account OK: {acct_msg}")
            else:
                st.warning(f"Account failed: {acct_msg}")
            if market_ok:
                st.success(f"MT5 market OK: {market_msg}")
            else:
                st.caption(f"MT5 market note: {market_msg}")

    with c1:
        if st.button("📌 Account Only", use_container_width=True, key="doo_account_only_read"):
            info, ok, msg = _safe_mt5_account_info()
            st.session_state.account_snapshot = info if isinstance(info, dict) else {}
            st.session_state.doo_prime_account_snapshot = st.session_state.account_snapshot
            st.success(msg) if ok else st.warning(msg)

    with c2:
        if st.button("🧩 Use Doo MT5 For All Tabs", use_container_width=True, key="doo_account_sync_all_tabs"):
            st.session_state.doo_prime_sync_to_shared = True
            acct_ok, acct_msg, market_ok, market_msg = _doo_prime_connect_mt5_account_and_market()
            st.success("Doo MT5 synced to shared dataframe.") if market_ok else st.warning(market_msg)

    # In non-compact/original mode keep the old save/snapshot controls.
    # In compact mode, account read stays visible but duplicated save/history buttons stay hidden.
    if not compact_mode:
        c0, c1, c2 = st.columns(3)

        with c0:
            st.caption("Account reader already available above.")

        with c1:
            if st.button("💾 Save Account Snapshot", use_container_width=True, key="home_doo_store"):
                info = st.session_state.get("account_snapshot", {})

                if not info:
                    st.warning("No account snapshot to save yet.")
                else:
                    positions = info.get("positions", []) or []

                    ok, msg = _safe_append_csv(
                        "doo_prime_account_history",
                        {
                            "time": pd.Timestamp.now(),
                            "balance": _safe_num(info.get("balance")),
                            "equity": _safe_num(info.get("equity")),
                            "margin": _safe_num(info.get("margin")),
                            "margin_free": _safe_num(info.get("margin_free")),
                            "margin_level": _safe_num(info.get("margin_level")),
                            "profit": _safe_num(info.get("profit")),
                            "positions": len(positions),
                        },
                    )

                    if ok:
                        st.success("Account snapshot saved.")
                    else:
                        st.error(msg)

        with c2:
            if st.button("🧹 Clear Screen Snapshot", use_container_width=True, key="home_doo_clear"):
                st.session_state.account_snapshot = {}
                _safe_rerun()

    info = st.session_state.get("account_snapshot", {})

    # IMPORTANT FIX:
    # Before, this panel returned immediately when no MT5/Doo account snapshot existed.
    # That made the Advanced Live Doo Prime Analytics area look blank when you connected
    # only Twelve Data. Now the market-analysis part still renders from st.session_state["last_df"].
    if not isinstance(info, dict) or not info:
        st.warning("No real Doo Prime/MT5 account snapshot yet. Market analytics below still work from the shared Twelve/MT5 candle data.")
        _show_advanced_doo_analytics({}, pd.DataFrame())
        st.info("For real balance, equity, margin, and positions: open local Doo Prime MT5, login, then click Read Real Doo Prime MT5 Account.")
        return

    balance = _safe_num(info.get("balance"))
    equity = _safe_num(info.get("equity"), balance)
    margin = _safe_num(info.get("margin"))
    free = _safe_num(info.get("margin_free"))
    margin_level = _safe_num(info.get("margin_level"))
    floating = _safe_num(info.get("profit"), equity - balance)

    drawdown = max(0.0, (balance - equity) / max(balance, 1e-9) * 100.0)
    margin_used_pct = margin / max(equity, 1e-9) * 100.0 if equity else 0.0
    free_pct = free / max(equity, 1e-9) * 100.0 if equity else 0.0

    positions_df = _positions_frame(info)

    st.markdown("#### Real Account Stats")

    emergency_action, _emergency_scenarios = _build_emergency_exit_decision(info, positions_df)

    row1 = st.columns(7)

    _metric_status(row1[0], "Balance", round(balance, 2))
    _metric_status(row1[1], "Equity", round(equity, 2))
    _metric_status(row1[2], "Floating P/L", round(floating, 2), "floating_pl")
    _metric_status(row1[3], "Margin Used %", round(margin_used_pct, 2), "margin_used_pct")
    _metric_status(row1[4], "Free Margin %", round(free_pct, 2), "free_margin_pct")
    _metric_status(row1[5], "Margin Level %", round(margin_level, 2), "margin_level")
    row1[6].metric("Emergency Exit", emergency_action.get("action_short", "READ"))
    row1[6].caption(emergency_action.get("reason", "Read account + market data first."))

    row2 = st.columns(6)

    open_count = len(positions_df)

    buy_count = int((positions_df.get("side", pd.Series(dtype=str)) == "BUY").sum()) if not positions_df.empty else 0
    sell_count = int((positions_df.get("side", pd.Series(dtype=str)) == "SELL").sum()) if not positions_df.empty else 0

    total_lots = float(positions_df["volume"].sum()) if "volume" in positions_df.columns else 0.0
    worst = float(positions_df["profit"].min()) if "profit" in positions_df.columns and len(positions_df) else 0.0
    best = float(positions_df["profit"].max()) if "profit" in positions_df.columns and len(positions_df) else 0.0

    _metric_status(row2[0], "Open Positions", open_count, "open_positions")
    _metric_status(row2[1], "BUY Count", buy_count)
    _metric_status(row2[2], "SELL Count", sell_count)
    _metric_status(row2[3], "Total Lots", round(total_lots, 2))
    _metric_status(row2[4], "Worst Position", round(worst, 2), "floating_pl")
    _metric_status(row2[5], "Drawdown %", round(drawdown, 2), "drawdown")

    st.markdown("#### Account Risk Status")

    risk_table = pd.DataFrame(
        [
            {
                "Risk Data": "Margin Level",
                "Value": round(margin_level, 2),
                "Status": _risk_status("margin_level", margin_level)[0],
                "Meaning": _risk_status("margin_level", margin_level)[1],
            },
            {
                "Risk Data": "Drawdown %",
                "Value": round(drawdown, 2),
                "Status": _risk_status("drawdown", drawdown)[0],
                "Meaning": _risk_status("drawdown", drawdown)[1],
            },
            {
                "Risk Data": "Margin Used %",
                "Value": round(margin_used_pct, 2),
                "Status": _risk_status("margin_used_pct", margin_used_pct)[0],
                "Meaning": _risk_status("margin_used_pct", margin_used_pct)[1],
            },
            {
                "Risk Data": "Free Margin %",
                "Value": round(free_pct, 2),
                "Status": _risk_status("free_margin_pct", free_pct)[0],
                "Meaning": _risk_status("free_margin_pct", free_pct)[1],
            },
            {
                "Risk Data": "Floating P/L",
                "Value": round(floating, 2),
                "Status": _risk_status("floating_pl", floating)[0],
                "Meaning": _risk_status("floating_pl", floating)[1],
            },
        ]
    )

    with st.expander("🛡️ Open account risk status table", expanded=False):
        st.dataframe(risk_table, use_container_width=True, hide_index=True)

    _show_advanced_doo_analytics(info, positions_df)

    st.markdown("#### Stop-Out / Blow-Out Proxy")

    stopout_level = st.number_input(
        "Broker stop-out level % proxy",
        min_value=1.0,
        max_value=500.0,
        value=50.0,
        step=5.0,
        key="doo_stopout_level",
        help="This is only a proxy. Real stop-out depends on broker rules, leverage, spread, commission, swap, and symbol margin.",
    )

    if margin > 0:
        estimated_stopout_equity = margin * stopout_level / 100.0
        loss_room = equity - estimated_stopout_equity

        b1, b2, b3 = st.columns(3)
        b1.metric("Estimated Stop-Out Equity", round(estimated_stopout_equity, 2))
        b2.metric("Approx Loss Room", round(loss_room, 2))
        b3.metric("Loss Room % of Equity", round(loss_room / max(equity, 1e-9) * 100.0, 2))

        if loss_room <= 0:
            st.error("Danger: equity is near or below this stop-out proxy.")
        elif loss_room < equity * 0.10:
            st.warning("Warning: small loss room remains by this proxy.")
        else:
            st.success("Loss room exists by this proxy.")
    else:
        st.info("No used margin detected, so stop-out proxy is inactive.")

    if not positions_df.empty:
        st.markdown("#### Open Positions")

        display_cols = [
            c for c in [
                "ticket",
                "symbol",
                "side",
                "volume",
                "price_open",
                "price_current",
                "pips",
                "profit",
                "profit_per_0.01",
                "swap",
                "commission",
                "hold_hours",
                "open_time",
            ]
            if c in positions_df.columns
        ]

        with st.expander("📌 Open full positions table", expanded=False):
            st.dataframe(positions_df[display_cols], use_container_width=True, height=300)

        csv = positions_df.to_csv(index=False).encode("utf-8")

        st.caption("⬇️ Open-position CSV export is centralized in the sidebar Download Center.")

        if "symbol" in positions_df.columns:
            st.markdown("#### Symbol Exposure")

            if "side" in positions_df.columns:
                expo = (
                    positions_df.groupby(["symbol", "side"], dropna=False)
                    .agg(
                        volume=("volume", "sum"),
                        profit=("profit", "sum"),
                        positions=("symbol", "count"),
                    )
                    .reset_index()
                )
            else:
                expo = (
                    positions_df.groupby("symbol")
                    .agg(
                        volume=("volume", "sum"),
                        profit=("profit", "sum"),
                        positions=("symbol", "count"),
                    )
                    .reset_index()
                )

            for col in ["volume", "profit"]:
                if col in expo.columns:
                    expo[col] = pd.to_numeric(expo[col], errors="coerce").round(2)

            with st.expander("📊 Open symbol exposure table", expanded=False):
                st.dataframe(expo, use_container_width=True, hide_index=True)

    else:
        st.info("No open positions returned from MT5.")

    st.markdown("#### Lot / Risk Helper")

    h1, h2, h3 = st.columns(3)

    with h1:
        lot = st.number_input(
            "Lot size to check",
            min_value=0.01,
            value=0.01,
            step=0.01,
            key="doo_lot_calc",
        )

    with h2:
        margin_per_001 = st.number_input(
            "Margin needed per 0.01 lot",
            min_value=1.0,
            value=150.0,
            step=10.0,
            key="doo_margin_per_001",
        )

    with h3:
        planned_entries = st.number_input(
            "Planned entries",
            min_value=1,
            value=1,
            step=1,
            key="doo_planned_entries",
        )

    need = margin_per_001 * (lot / 0.01) * planned_entries
    possible = int(free / (margin_per_001 * (lot / 0.01))) if lot and margin_per_001 else 0
    after_plan_free = free - need

    z = st.columns(3)
    z[0].metric("Margin Needed", round(need, 2))
    z[1].metric("Possible Entries", possible)
    z[2].metric("After-Plan Free Margin", round(after_plan_free, 2))

    if after_plan_free < 0:
        st.error("Planned entries need more margin than current free margin.")
    elif after_plan_free < free * 0.25:
        st.warning("Plan leaves low free margin. Consider smaller lot or fewer entries.")
    else:
        st.success("Plan is acceptable by this margin helper.")


# ==========================================================
# RISK PANEL
# ==========================================================

def risk_panel():
    st.markdown("### 🛡️ Risk Inner Tab — under Doo Prime only")

    acct = st.session_state.get("account_snapshot", {})

    balance = _safe_num(acct.get("balance"), 1000.0)
    equity = _safe_num(acct.get("equity"), balance)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        manual_balance = st.number_input(
            "Manual balance if no Doo data",
            value=float(balance),
            key="risk_manual_balance",
        )

    with c2:
        manual_equity = st.number_input(
            "Manual equity if no Doo data",
            value=float(equity),
            key="risk_manual_equity",
        )

    with c3:
        risk_pct = st.slider(
            "Risk per trade %",
            0.1,
            10.0,
            1.0,
            0.1,
            key="risk_pct_inner",
        )

    with c4:
        max_daily_loss_pct = st.slider(
            "Max daily loss %",
            1.0,
            25.0,
            5.0,
            0.5,
            key="risk_daily_loss_pct",
        )

    s1, s2, s3 = st.columns(3)

    with s1:
        sl_pips = st.number_input(
            "Stop loss pips",
            min_value=1.0,
            value=50.0,
            key="risk_sl_pips",
        )

    with s2:
        pip_value = st.number_input(
            "Pip value per 0.01 lot",
            min_value=0.01,
            value=1.0,
            key="risk_pip_value",
        )

    with s3:
        planned_trades = st.number_input(
            "Planned trades today",
            min_value=1,
            value=3,
            step=1,
            key="risk_planned_trades_today",
        )

    risk_money = manual_equity * risk_pct / 100.0
    lot_001_units = max(0.0, risk_money / max(sl_pips * pip_value, 1e-9))
    max_daily_loss = manual_equity * max_daily_loss_pct / 100.0
    drawdown = max(0.0, (manual_balance - manual_equity) / max(manual_balance, 1e-9) * 100.0)

    trades_to_daily_stop = int(max_daily_loss / max(risk_money, 1e-9))
    planned_total_risk = risk_money * planned_trades

    row = st.columns(6)

    row[0].metric("Risk $ / Trade", round(risk_money, 2))
    row[1].metric("Suggested 0.01-lot Units", round(lot_001_units, 2))
    row[2].metric("Suggested Lot", round(lot_001_units * 0.01, 2))
    row[3].metric("Max Daily Loss $", round(max_daily_loss, 2))
    row[4].metric("Current Drawdown %", round(drawdown, 2))
    row[5].metric("Trades to Daily Stop", trades_to_daily_stop)

    st.markdown("#### Planned Day Risk")

    p1, p2, p3 = st.columns(3)

    p1.metric("Planned Total Risk", round(planned_total_risk, 2))
    p2.metric("Planned Risk % of Equity", round(planned_total_risk / max(manual_equity, 1e-9) * 100.0, 2))
    p3.metric("Remaining Daily Risk Room", round(max_daily_loss - planned_total_risk, 2))

    if planned_total_risk > max_daily_loss:
        st.error("Planned trades exceed your max daily loss rule.")
    elif planned_total_risk > max_daily_loss * 0.7:
        st.warning("Planned trades use more than 70% of daily risk room.")
    else:
        st.success("Planned trades are inside your daily risk rule.")

    risk_table = pd.DataFrame(
        [
            {
                "Risk Item": "Risk per trade",
                "Value": round(risk_pct, 2),
                "Status": "GOOD" if risk_pct <= 2 else "BAD" if risk_pct <= 5 else "DANGEROUS",
                "Meaning": "Lower risk gives more survival time.",
            },
            {
                "Risk Item": "Drawdown %",
                "Value": round(drawdown, 2),
                "Status": _risk_status("drawdown", drawdown)[0],
                "Meaning": _risk_status("drawdown", drawdown)[1],
            },
            {
                "Risk Item": "Planned total risk",
                "Value": round(planned_total_risk, 2),
                "Status": "GOOD" if planned_total_risk <= max_daily_loss else "DANGEROUS",
                "Meaning": "Must stay below daily max loss.",
            },
        ]
    )

    with st.expander("📋 Open risk explanation table", expanded=False):
        st.dataframe(risk_table, use_container_width=True, hide_index=True)

    if st.button("💾 Save Risk Snapshot", use_container_width=True, key="risk_save_snapshot"):
        ok, msg = _safe_append_csv(
            "risk_snapshots",
            {
                "time": pd.Timestamp.now(),
                "balance": manual_balance,
                "equity": manual_equity,
                "risk_pct": risk_pct,
                "risk_money": risk_money,
                "sl_pips": sl_pips,
                "pip_value_per_001": pip_value,
                "lot_001_units": lot_001_units,
                "suggested_lot": lot_001_units * 0.01,
                "max_daily_loss_pct": max_daily_loss_pct,
                "max_daily_loss": max_daily_loss,
                "drawdown_pct": drawdown,
                "planned_trades": planned_trades,
                "planned_total_risk": planned_total_risk,
            },
        )

        if ok:
            st.success("Risk snapshot saved. It will not duplicate automatically on every refresh.")
        else:
            st.error(msg)


# ==========================================================
# DOO PRIME PANEL
# ==========================================================

def doo_prime_panel():
    st.markdown("### 🏦 Doo Prime — Account + Risk + Live Analysis")
    st.caption("Instant compact mode: one button row only. No duplicate account/read/refresh buttons. Only the selected section renders.")

    if "doo_prime_lazy_section_account" not in st.session_state:
        st.session_state.doo_prime_lazy_section_account = "🏦 Account"

    def _set_doo_section_account(name):
        st.session_state.doo_prime_lazy_section_account = name
        st.session_state["ui_navigation_click_ts"] = time.time()

    b1, b2, b3, b4 = st.columns(4)
    current = st.session_state.get("doo_prime_lazy_section_account", "🏦 Account")
    with b1:
        st.button(("✅ " if current == "🏦 Account" else "") + "🏦 Account", use_container_width=True, key="doo_account_nav_account", on_click=_set_doo_section_account, args=("🏦 Account",))
    with b2:
        st.button(("✅ " if current == "🛡️ Risk" else "") + "🛡️ Risk", use_container_width=True, key="doo_account_nav_risk", on_click=_set_doo_section_account, args=("🛡️ Risk",))
    with b3:
        st.button(("✅ " if current == "📜 History" else "") + "📜 History", use_container_width=True, key="doo_account_nav_history", on_click=_set_doo_section_account, args=("📜 History",))
    with b4:
        if st.button("🔄 Refresh", use_container_width=True, key="doo_account_nav_refresh"):
            acct_ok, acct_msg, market_ok, market_msg = _doo_prime_connect_mt5_account_and_market()
            if acct_ok or market_ok:
                st.success(f"Doo refresh: account={acct_ok}, market={market_ok}")
            else:
                st.warning(f"Doo refresh failed: {acct_msg} | {market_msg}")

    st.caption(f"Current Source: {st.session_state.get('source', 'DISCONNECTED')}")

    section = st.session_state.get("doo_prime_lazy_section_account", "🏦 Account")
    st.session_state["doo_prime_compact_controls"] = True
    try:
        if section == "🏦 Account":
            doo_prime_account_panel()
            return
        if section == "🛡️ Risk":
            risk_panel()
            return
        hist_section = choice_buttons(
            "History type",
            ["Risk Snapshots", "Doo Prime Account History"],
            key="doo_prime_history_lazy_section_account",
            columns=2,
            default="Risk Snapshots",
        )
        if hist_section == "Risk Snapshots":
            risk_hist = _safe_read_csv("risk_snapshots")
            if risk_hist.empty:
                st.info("No risk snapshots yet. Open Risk once; it auto-saves when results exist.")
            else:
                with st.expander("📜 Open risk snapshot history table", expanded=True):
                    st.dataframe(risk_hist.drop_duplicates().tail(300), use_container_width=True)
            return
        acct_hist = _safe_read_csv("doo_prime_account_history")
        if acct_hist.empty:
            st.info("No Doo Prime account history yet. Open Account once; it auto-saves after account data is read.")
        else:
            acct_hist = acct_hist.drop_duplicates().tail(300)
            with st.expander("🏦 Open Doo Prime account history table", expanded=True):
                st.dataframe(acct_hist, use_container_width=True)
            chart_cols = [c for c in ["balance", "equity", "margin_free"] if c in acct_hist.columns]
            if chart_cols and "time" in acct_hist.columns:
                chart_df = acct_hist.copy()
                chart_df["time"] = pd.to_datetime(chart_df.get("time"), errors="coerce")
                chart_df = chart_df.dropna(subset=["time"])
                if not chart_df.empty:
                    st.line_chart(chart_df.set_index("time")[chart_cols])
    finally:
        st.session_state["doo_prime_compact_controls"] = False


# ==========================================================
# HOME SHOW
# ==========================================================

def show():
    st.markdown("# 🏠 Home — Start Page")
    st.caption("Fast mode: Home launcher and Doo Prime render one section at a time.")

    section = st.radio(
        "Open Home section",
        ["🏠 Launcher", "🏦 Doo Prime"],
        horizontal=True,
        key="account_home_lazy_section",
    )

    if section == "🏦 Doo Prime":
        doo_prime_panel()
        return

    home_symbol = st.text_input(
        "Symbol space / other symbol possible",
        value=st.session_state.get("symbol", "XAUUSD"),
        key="home_symbol",
        help="Auto-filled XAUUSD, but you can type EURUSD, GBPUSD, BTCUSD if supported.",
    )
    st.session_state.symbol = str(home_symbol or "XAUUSD").upper().strip()

    grid = st.columns(4)
    safe_tabs = DEFAULT_TABS if DEFAULT_TABS else ["home", "engine", "backtest", "guide", "account"]
    for i, tab in enumerate(safe_tabs):
        with grid[i % 4]:
            if st.button(f"Open {tab}", use_container_width=True, key=f"home_open_{tab}"):
                st.session_state.tab_choice = tab
                _safe_log_event(f"Home open: {tab}")
                _safe_close_sidebar()
                _safe_rerun()

    with st.expander("🔌 Optional old Home connector controls", expanded=False):
        api_key = st.text_input(
            "Twelve Data API key",
            value=st.session_state.get("twelve_api_key", ""),
            type="password",
            key="home_twelve_api_key",
        )
        st.session_state.twelve_api_key = api_key
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("MT5 M1", use_container_width=True, key="home_mt5_only"):
                _safe_manual_connect("mt5", st.session_state.symbol, st.session_state.twelve_api_key, bars=5000, timeframe="M1")
        with c2:
            if st.button("MT5 M2 100D", use_container_width=True, key="home_mt5_m2"):
                _safe_manual_connect("mt5", st.session_state.symbol, st.session_state.twelve_api_key, bars=80000, timeframe="M2")
        with c3:
            if st.button("Twelve Only", use_container_width=True, key="home_twelve_only"):
                _safe_manual_connect("twelve", st.session_state.symbol, st.session_state.twelve_api_key, bars=5000, timeframe="M1")
        with c4:
            if st.button("Disconnect", use_container_width=True, key="home_disconnect"):
                st.session_state.connected = False
                st.session_state.source = "DISCONNECTED"
                st.session_state.last_df = None
                st.success("Disconnected.")
                _safe_rerun()

    st.metric("Current Source", st.session_state.get("source", "DISCONNECTED"))
    df = st.session_state.get("last_df")
    if df is not None:
        q = _safe_quant_stack(df)
        m = st.columns(4)
        m[0].metric("Safe 12H Bias", q.get("bias", "WAIT"))
        m[1].metric("Safety /10", q.get("scale10", 0))
        m[2].metric("Safety %", q.get("safe_pct", 0))
        m[3].metric("Symbol", st.session_state.symbol)
        with st.expander("Home quant detail", expanded=False):
            st.json(q)
        auto_save_home = st.checkbox("Auto-save home snapshot safely every 60 seconds", value=False, key="home_auto_save_snapshot")
        if auto_save_home:
            _save_once_per_60_seconds("home_snapshots", {"time": pd.Timestamp.now(), "symbol": st.session_state.symbol, **q}, "home_last_auto_save_time")
    else:
        st.info("No market data connected yet. Click MT5 M1, MT5 M2 100D, or Twelve Only.")
