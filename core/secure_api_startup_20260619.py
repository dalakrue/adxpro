"""Secure API-secret resolution and guarded authenticated startup.

Secrets are read server-side and never returned to UI code.  The guarded startup
is idempotent per completed H1 candle and keeps manual Run Calculation available.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Mapping, MutableMapping

import pandas as pd

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

_LOCK = threading.Lock()


def _secret_path(*parts: str) -> str:
    if st is None:
        return ""
    try:
        value: Any = st.secrets
        for part in parts:
            value = value[part]
        return str(value or "").strip()
    except Exception:
        return ""


def _secret_bool(section: str, name: str, default: bool) -> bool:
    value = _secret_path(section, name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on", "enabled"}


def resolve_api_key(provider: str, state: Mapping[str, Any] | None = None) -> str:
    """Resolve a server-side secret; the caller must never put it in a widget value."""
    state = state or {}
    provider = str(provider or "").strip().lower()
    if provider in {"finnhub", "finn"}:
        return (
            _secret_path("api_keys", "finnhub")
            or os.getenv("FINNHUB_API_KEY", "").strip()
            or str(state.get("finnhub_api_key") or "").strip()
        )
    if provider in {"second_api", "twelve", "twelve_data", "market"}:
        return (
            _secret_path("api_keys", "second_api")
            or _secret_path("api_keys", "twelve_data")
            or _secret_path("api_keys", "twelve")
            or os.getenv("TWELVE_DATA_API_KEY", "").strip()
            or os.getenv("TWELVE_API_KEY", "").strip()
            or str(state.get("twelve_api_key") or "").strip()
        )
    return ""


def secure_secret_status(state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    finnhub_secret = bool(_secret_path("api_keys", "finnhub") or os.getenv("FINNHUB_API_KEY"))
    second_secret = bool(
        _secret_path("api_keys", "second_api") or _secret_path("api_keys", "twelve_data")
        or _secret_path("api_keys", "twelve") or os.getenv("TWELVE_DATA_API_KEY") or os.getenv("TWELVE_API_KEY")
    )
    return {
        "finnhub_configured": bool(finnhub_secret or state.get("finnhub_api_key")),
        "second_api_configured": bool(second_secret or state.get("twelve_api_key")),
        "finnhub_source": "Streamlit Secrets" if finnhub_secret else ("Temporary session replacement" if state.get("finnhub_api_key") else "Not configured"),
        "second_api_source": "Streamlit Secrets" if second_secret else ("Temporary session replacement" if state.get("twelve_api_key") else "Not configured"),
    }


def initialize_secure_settings(state: MutableMapping[str, Any]) -> None:
    state.setdefault("use_secure_api_keys_20260619", True)
    state.setdefault("auto_connect_after_login_20260619", _secret_bool("automation", "auto_connect", True))
    state.setdefault("auto_calculate_new_h1_20260619", _secret_bool("automation", "auto_run_on_login", True))
    state.setdefault("open_lunch_after_auto_run_20260619", _secret_bool("automation", "open_lunch_after_calculation", True))
    state.setdefault("auto_run_cooldown_minutes_20260619", 5)


def _latest_h1(frame: Any) -> pd.Timestamp | None:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    aliases = ("time", "datetime", "timestamp", "date")
    normalized = {str(col).lower().replace("_", " "): col for col in frame.columns}
    column = next((normalized.get(name) for name in aliases if normalized.get(name) is not None), None)
    if column is None:
        return None
    values = pd.to_datetime(frame[column], errors="coerce", utc=True).dropna()
    return pd.Timestamp(values.max()) if not values.empty else None


def _canonical_latest(state: MutableMapping[str, Any]) -> pd.Timestamp | None:
    try:
        from core.canonical_runtime_20260617 import get_canonical
        canonical = get_canonical(state)
    except Exception:
        canonical = state.get("canonical_result_20260617") or {}
    if not isinstance(canonical, Mapping):
        return None
    value = canonical.get("latest_completed_candle_time") or canonical.get("latest_completed_h1_timestamp")
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return pd.Timestamp(parsed) if pd.notna(parsed) else None


def _connect_market(state: MutableMapping[str, Any]) -> dict[str, Any]:
    key = resolve_api_key("second_api", state) if state.get("use_secure_api_keys_20260619", True) else str(state.get("twelve_api_key") or "")
    mode = str(state.get("connector_mode") or "twelve")
    if mode in {"twelve", "fallback"} and not key and state.get("last_df") is None:
        return {"ok": False, "status": "SKIPPED", "message": "Second market API key is not configured."}
    from core.connectors.data_parts.session import manual_connect
    frame, ok, source, message = manual_connect(
        mode=mode,
        symbol=str(state.get("symbol") or "EURUSD"),
        api_key=key,
        bars=int(state.get("connector_bars") or 600),
        timeframe=str(state.get("timeframe") or "H1"),
        bridge_url=str(state.get("doo_bridge_url") or ""),
        bridge_token=str(state.get("doo_bridge_token") or ""),
        allow_demo=bool(state.get("allow_safe_demo", False)),
    )
    return {"ok": bool(ok), "source": source, "message": message, "rows": len(frame) if isinstance(frame, pd.DataFrame) else 0}


def _validate_finnhub_once(state: MutableMapping[str, Any]) -> dict[str, Any]:
    key = resolve_api_key("finnhub", state) if state.get("use_secure_api_keys_20260619", True) else str(state.get("finnhub_api_key") or "")
    if not key:
        return {"ok": False, "status": "SKIPPED", "message": "Finnhub key is not configured."}
    now = time.time()
    last = float(state.get("secure_finnhub_validation_ts_20260619", 0.0) or 0.0)
    if now - last < 3600 and state.get("finnhub_connected"):
        return {"ok": True, "status": "CACHED"}
    from core.finnhub_connector import connect
    result = connect(key)
    state["secure_finnhub_validation_ts_20260619"] = now
    return {"ok": bool(result.get("ok")), "status": result.get("availability", "UNKNOWN"), "message": result.get("message", "")}


def run_guarded_startup(state: MutableMapping[str, Any], home_namespace: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run at most once for a newer completed H1 after authenticated login."""
    initialize_secure_settings(state)
    result: dict[str, Any] = {"ok": True, "status": "NO_ACTION", "auto_connected": False, "auto_calculated": False}
    if not state.get("new7_auth_logged_in") or state.get("new7_auth_guest"):
        result.update(ok=False, status="AUTH_REQUIRED")
        state["secure_startup_status_20260619"] = result
        return result

    now = time.time()
    cooldown = max(1, int(state.get("auto_run_cooldown_minutes_20260619", 5) or 5)) * 60
    last_attempt = float(state.get("secure_startup_attempt_ts_20260619", 0.0) or 0.0)
    if now - last_attempt < min(cooldown, 60):
        result["status"] = "RERUN_GUARD"
        return result
    state["secure_startup_attempt_ts_20260619"] = now

    if state.get("auto_connect_after_login_20260619", True):
        try:
            market = _connect_market(state) if not state.get("connected") or not isinstance(state.get("last_df"), pd.DataFrame) else {"ok": True, "status": "ALREADY_CONNECTED"}
            finnhub = _validate_finnhub_once(state)
            result["market_connection"] = market
            result["finnhub_connection"] = finnhub
            result["auto_connected"] = bool(market.get("ok") or finnhub.get("ok"))
        except Exception as exc:
            result["connection_error"] = f"{type(exc).__name__}: {exc}"

    latest = _latest_h1(state.get("last_df"))
    published = _canonical_latest(state)
    result["latest_h1"] = latest.isoformat() if latest is not None else None
    result["published_h1"] = published.isoformat() if published is not None else None
    newer = latest is not None and (published is None or latest > published)
    if not state.get("auto_calculate_new_h1_20260619", True) or not newer:
        result["status"] = "CURRENT" if latest is not None else "DATA_NOT_READY"
        state["secure_startup_status_20260619"] = result
        return result
    last_calc = float(state.get("secure_auto_calculation_ts_20260619", 0.0) or 0.0)
    if now - last_calc < cooldown:
        result["status"] = "COOLDOWN"
        state["secure_startup_status_20260619"] = result
        return result
    if not _LOCK.acquire(blocking=False):
        result["status"] = "GENERATION_LOCKED"
        state["secure_startup_status_20260619"] = result
        return result
    try:
        from core.settings_run_orchestrator_20260617 import run_settings_calculation
        calculation = run_settings_calculation(dict(home_namespace or {}))
        result["calculation"] = calculation
        result["auto_calculated"] = bool((calculation.get("canonical") or {}).get("ok"))
        result["status"] = "CALCULATED" if result["auto_calculated"] else "CALCULATION_FAILED"
        state["secure_auto_calculation_ts_20260619"] = time.time()
        if result["auto_calculated"] and state.get("open_lunch_after_auto_run_20260619", True):
            state.update({"active_page": "Lunch", "tab_choice": "Lunch", "active_subpage": "", "lunch_active_subpage": ""})
    except Exception as exc:
        result.update(ok=False, status="CALCULATION_FAILED", calculation_error=f"{type(exc).__name__}: {exc}")
    finally:
        _LOCK.release()
    state["secure_startup_status_20260619"] = result
    return result


__all__ = [
    "resolve_api_key", "secure_secret_status", "initialize_secure_settings", "run_guarded_startup",
]
