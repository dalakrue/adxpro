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
    from core.data_connectors import manual_connect, mt5_account_info
except Exception:
    manual_connect = None
    mt5_account_info = None

try:
    from core.quant_models import quant_stack
except Exception:
    quant_stack = None

try:
    from core.database import append_csv, read_csv
except Exception:
    append_csv = None
    read_csv = None


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
    fat_tail_z = latest_ret / max(ret_std, 1e-9)
    kurt = float(ret_window.kurt()) if len(ret_window) >= 20 else 0.0

    accel_abs = abs(sec10_speed - min1_speed) * 60.0
    direction = _trend_direction(last10["price"])

    one_way_score = min(100.0, max(0.0, eff_now * 0.65 + min(fat_tail_z, 4.0) * 8.0 + min(abs(min1_pct) * 20.0, 20.0)))
    trust = min(100.0, max(0.0, one_way_score - eff_falling * 0.7))

    if eff_now >= 75 and fat_tail_z >= 2.5 and eff_falling >= 8:
        regime = "ONE-WAY TREND REACHING LIMIT / EXHAUSTION RISK"
    elif eff_rising >= 8 and eff_now >= 55:
        regime = f"ONE-WAY TREND STARTING / CONTINUING {direction}"
    elif eff_now >= 70:
        regime = f"ONE-WAY TREND CONTINUES {direction}"
    elif eff_falling >= 12:
        regime = "ONE-WAY TREND STOPPING / CHOP RISK"
    elif fat_tail_z >= 3:
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


def _show_advanced_doo_analytics(info, positions_df):
    st.markdown("#### ⚡ Advanced Live Doo Prime Analytics")
    st.caption("Uses your connected market dataframe plus real account snapshot. It is analytical guidance, not a guaranteed prediction.")

    hist = _record_account_live_snapshot(info)
    df = st.session_state.get("last_df")
    market, market_frame = _calc_market_analytics(df)

    if not market:
        st.info("Connect MT5/Twelve market data first to calculate price speed, derivative, fat-tail, and directional efficiency.")
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
        r2[0].metric("Fat Tail Z", round(market["fat_tail_z"], 2))
        r2[0].caption(f"{_status_badge(fs)} {fs}: {fn}")
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
            {"Data": "Fat Tail Z", "Current": round(market["fat_tail_z"], 2), "Meaning": "How unusual the latest move is versus recent returns. Above 2 is important; above 3 is extreme."},
            {"Data": "Directional Efficiency", "Current": round(market["directional_efficiency"], 2), "Meaning": "Net direction divided by total path. High value means cleaner one-way trend."},
            {"Data": "Rising Efficiency", "Current": round(market["efficiency_rising"], 2), "Meaning": "Positive increase means trend quality is improving and one-way movement may be starting."},
            {"Data": "Falling Efficiency", "Current": round(market["efficiency_falling"], 2), "Meaning": "Positive value means one-way trend quality is decaying; trend may be near limit or stopping."},
            {"Data": "Derivative / Acceleration", "Current": round(market["accel_abs"], 4), "Meaning": "Difference between short speed and minute speed. High value means price movement is accelerating."},
        ])
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
        st.dataframe(combo_df, use_container_width=True, hide_index=True)

    st.markdown("##### Margin Level Change Speed")
    m_sec = _margin_change_from_history(hist, 1)
    m_min = _margin_change_from_history(hist, 60)
    m_hour = _margin_change_from_history(hist, 3600)
    mr = st.columns(3)
    for col, label, val in zip(mr, ["Per Second", "Per Minute", "Per Hour"], [m_sec, m_min, m_hour]):
        ms, mn = _analytics_status("margin_level_change", val)
        col.metric(f"Margin Level Change {label}", round(val, 4))
        col.caption(f"{_status_badge(ms)} {ms}: {mn}")

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

def doo_prime_account_panel():
    st.markdown("### 🏦 Doo Prime / MT5 Account Reader")

    st.caption(
        "Reads real local MT5/Doo Prime data when MetaTrader 5 is open and logged in. "
        "On Streamlit Cloud it safely shows MT5 unavailable instead of crashing."
    )

    # Compact navigation fix: the parent Doo Prime panel owns the single
    # Account / Risk / History / Refresh button row.  This prevents duplicate
    # account/read/save buttons and makes inner-tab switching instant.
    if not st.session_state.get("doo_prime_compact_controls", False):
        c0, c1, c2 = st.columns(3)

        with c0:
            if st.button("🔍 Read Real Doo Prime MT5 Account", use_container_width=True, key="home_doo_read"):
                info, ok, msg = _safe_mt5_account_info()
                st.session_state.account_snapshot = info

                if ok:
                    st.success(msg)
                else:
                    st.warning(msg)

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

    if not info:
        st.info("Open your local Doo Prime MetaTrader 5, login, then click Read Real Doo Prime MT5 Account.")
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

    row1 = st.columns(6)

    _metric_status(row1[0], "Balance", round(balance, 2))
    _metric_status(row1[1], "Equity", round(equity, 2))
    _metric_status(row1[2], "Floating P/L", round(floating, 2), "floating_pl")
    _metric_status(row1[3], "Margin Used %", round(margin_used_pct, 2), "margin_used_pct")
    _metric_status(row1[4], "Free Margin %", round(free_pct, 2), "free_margin_pct")
    _metric_status(row1[5], "Margin Level %", round(margin_level, 2), "margin_level")

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

        st.dataframe(positions_df[display_cols], use_container_width=True, height=300)

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
    st.markdown("### 🏦 Doo Prime — Account + Risk")

    st.caption("Duplicate Risk tab removed from sidebar. Risk is only here under Doo Prime.")

    doo_tabs = st.tabs(["🏦 Real Account Stats", "🛡️ Risk Calculator", "📜 Risk / Account History"])

    with doo_tabs[0]:
        doo_prime_account_panel()

    with doo_tabs[1]:
        risk_panel()

    with doo_tabs[2]:
        h1, h2 = st.tabs(["Risk Snapshots", "Doo Prime Account History"])

        with h1:
            risk_hist = _safe_read_csv("risk_snapshots")

            if risk_hist.empty:
                st.info("No risk snapshots yet. Save one from Risk Calculator.")
            else:
                st.dataframe(risk_hist.drop_duplicates().tail(300), use_container_width=True)

        with h2:
            acct_hist = _safe_read_csv("doo_prime_account_history")

            if acct_hist.empty:
                st.info("No Doo Prime account history yet. Save one from Real Account Stats.")
            else:
                acct_hist = acct_hist.drop_duplicates().tail(300)
                st.dataframe(acct_hist, use_container_width=True)

                chart_cols = [c for c in ["balance", "equity", "margin_free"] if c in acct_hist.columns]

                if chart_cols and "time" in acct_hist.columns:
                    chart_df = acct_hist.copy()
                    chart_df["time"] = pd.to_datetime(chart_df.get("time"), errors="coerce")
                    chart_df = chart_df.dropna(subset=["time"])

                    if not chart_df.empty:
                        st.line_chart(chart_df.set_index("time")[chart_cols])


# ==========================================================
# HOME SHOW
# ==========================================================

def show():
    st.markdown("# 🏠 Home — Start Page")

    st.caption("Launcher, connection buttons, and upgraded Doo Prime account/risk stats are combined here.")

    home_tabs = st.tabs(["🏠 Launcher", "🏦 Doo Prime"])

    with home_tabs[0]:
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

        st.markdown("---")

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
                _safe_manual_connect(
                    "mt5",
                    st.session_state.symbol,
                    st.session_state.twelve_api_key,
                    bars=5000,
                    timeframe="M1",
                )

        with c2:
            if st.button("MT5 M2 100D", use_container_width=True, key="home_mt5_m2"):
                _safe_manual_connect(
                    "mt5",
                    st.session_state.symbol,
                    st.session_state.twelve_api_key,
                    bars=80000,
                    timeframe="M2",
                )

        with c3:
            if st.button("Twelve Only", use_container_width=True, key="home_twelve_only"):
                _safe_manual_connect(
                    "twelve",
                    st.session_state.symbol,
                    st.session_state.twelve_api_key,
                    bars=5000,
                    timeframe="M1",
                )

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

            with st.expander("Home quant detail"):
                st.json(q)

            auto_save_home = st.checkbox(
                "Auto-save home snapshot safely every 60 seconds",
                value=False,
                key="home_auto_save_snapshot",
            )

            if auto_save_home:
                _save_once_per_60_seconds(
                    "home_snapshots",
                    {
                        "time": pd.Timestamp.now(),
                        "symbol": st.session_state.symbol,
                        **q,
                    },
                    "home_last_auto_save_time",
                )
        else:
            st.info("No market data connected yet. Click MT5 M1, MT5 M2 100D, or Twelve Only.")

    with home_tabs[1]:
        doo_prime_panel()
