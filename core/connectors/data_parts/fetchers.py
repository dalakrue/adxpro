import time
import pandas as pd
import requests
import streamlit as st

from core.common import synthetic_ohlc, log_event

try:
    from core.system_contract import (
        mark_data_version,
        update_connection_health,
        update_data_quality_from_session,
        record_system_event,
    )
except Exception:  # keeps old connector usable even if upgrade file is missing
    mark_data_version = None
    update_connection_health = None
    update_data_quality_from_session = None
    record_system_event = None


MT5_TIMEFRAMES = {
    "M1": "TIMEFRAME_M1",
    "M2": "TIMEFRAME_M2",
    "M3": "TIMEFRAME_M3",
    "M4": "TIMEFRAME_M4",
    "M5": "TIMEFRAME_M5",
    "M10": "TIMEFRAME_M10",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1",
}

TWELVE_INTERVALS = {
    "M1": "1min",
    "M2": "1min",
    "M3": "1min",
    "M4": "1min",
    "M5": "5min",
    "M10": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1day",
}




from .utils import _safe_log, _import_mt5, _clean_symbol, _resolve_mt5_symbol, _twelve_symbol, _normalize_ohlc, resample_ohlc

def fetch_mt5(symbol="XAUUSD", timeframe="M1", bars=500):
    mt5 = _import_mt5()

    if mt5 is None:
        return None, False, "MetaTrader5 library not installed or unsupported here"

    try:
        if not mt5.initialize():
            mt5.shutdown()
            if not mt5.initialize():
                try:
                    err = mt5.last_error()
                except Exception:
                    err = ""
                return None, False, f"MT5 initialize failed. Open Doo Prime MT5 terminal, login, then retry. {err}"

        requested_symbol = _clean_symbol(symbol)
        symbol, selected, symbol_note = _resolve_mt5_symbol(mt5, requested_symbol)
        if not selected:
            return None, False, symbol_note

        timeframe = str(timeframe or "M1").upper()

        tf_name = MT5_TIMEFRAMES.get(timeframe, "TIMEFRAME_M1")
        tf = getattr(mt5, tf_name, getattr(mt5, "TIMEFRAME_M1"))

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, int(bars))

        if rates is None or len(rates) < 30:
            if timeframe in ["M2", "M3", "M4", "M10"]:
                rates = mt5.copy_rates_from_pos(
                    symbol,
                    getattr(mt5, "TIMEFRAME_M1"),
                    0,
                    int(bars) * 5,
                )

                if rates is None or len(rates) < 30:
                    try:
                        err = mt5.last_error()
                    except Exception:
                        err = ""
                    return None, False, f"No MT5 {timeframe}/M1 rates returned for {symbol}. {err}"

                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s", errors="coerce")
                df = _normalize_ohlc(df)
                return resample_ohlc(df, timeframe), True, f"MT5 M1 resampled to {timeframe}"

            try:
                err = mt5.last_error()
            except Exception:
                err = ""
            return None, False, f"No MT5 rates returned for {symbol}. Check Market Watch, broker symbol, and internet/login. {err}"

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", errors="coerce")
        df = _normalize_ohlc(df)

        note = f"MT5 connected {timeframe}"
        if symbol_note != "exact":
            note = f"{note} ({symbol_note})"
        return df, True, note

    except Exception as e:
        return None, False, f"MT5 error: {e}"

def fetch_twelve(symbol="XAUUSD", api_key="", interval="1min", bars=500):
    try:
        if not api_key:
            return None, False, "Missing Twelve Data API key"

        sym = _twelve_symbol(symbol)

        requested_bars = max(1, int(bars or 500))
        # Twelve Data rejects very large outputsize values. Keep the app fast and
        # prevent API Health from showing "Invalid outputsize" when the user
        # chooses 60,000+ candles for deep panels. Deep analysis can still use
        # the cached/shared dataframe, while Twelve requests stay valid.
        safe_bars = min(requested_bars, 5000)

        params = {
            "symbol": sym,
            "interval": interval,
            "outputsize": int(safe_bars),
            "apikey": api_key,
            "format": "JSON",
        }

        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params=params,
            timeout=20,
        )

        try:
            data = r.json()
        except Exception:
            return None, False, f"Twelve Data invalid response: HTTP {r.status_code}"

        if "values" not in data:
            return None, False, str(data)[:250]

        df = pd.DataFrame(data["values"]).iloc[::-1].reset_index(drop=True)

        if "datetime" in df.columns:
            df["time"] = pd.to_datetime(df["datetime"], errors="coerce")

        df = _normalize_ohlc(df)

        cap_note = f" capped {safe_bars:,}/{requested_bars:,}" if requested_bars > safe_bars else ""
        return df, True, f"Twelve Data connected {interval}{cap_note}"

    except Exception as e:
        return None, False, f"Twelve error: {e}"

def fetch_doo_bridge(
    symbol="XAUUSD",
    timeframe="M1",
    bars=500,
    bridge_url="",
    bridge_token="",
):
    try:
        bridge_url = str(bridge_url or "").strip()

        if not bridge_url:
            return None, False, "Missing Doo Bridge URL"

        headers = {}

        if bridge_token:
            headers["Authorization"] = f"Bearer {bridge_token}"

        params = {
            "symbol": _clean_symbol(symbol),
            "timeframe": str(timeframe or "M1").upper(),
            "bars": int(bars),
        }

        r = requests.get(bridge_url, params=params, headers=headers, timeout=25)

        try:
            data = r.json()
        except Exception:
            return None, False, f"Doo Bridge invalid response: HTTP {r.status_code}"

        if not data.get("ok", False):
            return None, False, str(data.get("message", data))[:250]

        candles = data.get("candles", [])

        if not candles:
            return None, False, "Doo Bridge returned no candles"

        df = pd.DataFrame(candles)
        df = _normalize_ohlc(df)

        if "account" in data:
            st.session_state.account_snapshot = data.get("account", {})

        if "positions" in data:
            st.session_state.doo_positions = data.get("positions", [])

        return df, True, "Doo Bridge connected"

    except Exception as e:
        return None, False, f"Doo Bridge error: {e}"

