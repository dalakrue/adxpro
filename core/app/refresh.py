"""Connector refresh controls that remain separate from Run Calculation."""
from __future__ import annotations

import hashlib
import time
from typing import Any, Mapping, MutableMapping

import pandas as pd
import streamlit as st

from core.data_connectors import maybe_refresh, refresh_now


def _source_signature(frame: Any, *, source: str, symbol: str, timeframe: str) -> str:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return hashlib.sha256(f"{source}|{symbol}|{timeframe}|EMPTY".encode()).hexdigest()[:24]
    columns = [c for c in ("time", "Time", "Datetime", "open", "high", "low", "close", "volume") if c in frame.columns]
    sample = frame.loc[:, columns].tail(32) if columns else frame.tail(32)
    digest = pd.util.hash_pandas_object(sample, index=True).values.tobytes()
    return hashlib.sha256(f"{source}|{symbol}|{timeframe}|{len(frame)}".encode() + digest).hexdigest()[:24]


def _quality(frame: Any) -> dict[str, Any]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return {"rows": 0, "missing": "BLOCKED", "duplicates": "UNKNOWN", "latest_completed_h1": None}
    time_col = next((c for c in ("time", "Time", "Datetime", "DateTime", "Timestamp") if c in frame.columns), None)
    latest = None
    duplicates = 0
    if time_col:
        parsed = pd.to_datetime(frame[time_col], errors="coerce", utc=True)
        valid = parsed.dropna()
        latest = valid.max().isoformat() if not valid.empty else None
        duplicates = int(parsed.duplicated().sum())
    missing = int(frame.isna().sum().sum())
    return {
        "rows": int(len(frame)),
        "missing": "PASS" if missing == 0 else f"WARNING ({missing})",
        "duplicates": "PASS" if duplicates == 0 else f"WARNING ({duplicates})",
        "latest_completed_h1": latest,
    }


def _clear_source_dependent_presentation(state: MutableMapping[str, Any]) -> None:
    prefixes = (
        "lunch_bi_visual_cache", "lunch_visualization_export", "lunch_red_chart_alpha",
        "canonical_copy_", "canonical_export_", "ai_grounded_cache_", "ai_retrieval_",
        "history_search_result_", "temporary_dataframe_", "presentation_cache_20260621",
    )
    protected = ("canonical_result", "canonical_calculation", "history", "connector", "user_settings")
    for key in list(state.keys()):
        text = str(key)
        if any(token in text for token in protected):
            continue
        if text.startswith(prefixes):
            state.pop(key, None)
    try:
        from core.adaptive_presentation_cache_20260621 import clear_reconstructable
        clear_reconstructable(state)
    except Exception:
        pass


def refresh_data(state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    """Force the existing connector path without running the calculation engine."""
    state = state if state is not None else st.session_state
    before_generation = state.get("canonical_calculation_generation_20260617", state.get("calculation_generation"))
    before_canonical = state.get("canonical_result_20260617") or state.get("canonical_result")
    started = time.perf_counter()
    try:
        frame, ok, source, message = refresh_now(
            symbol=state.get("symbol", "XAUUSD"),
            api_key=state.get("twelve_api_key", ""),
            bridge_url=state.get("doo_bridge_url", ""),
            bridge_token=state.get("doo_bridge_token", ""),
            bars=state.get("connector_bars", 600),
            timeframe=state.get("timeframe", "M1"),
        )
        quality = _quality(frame)
        signature = _source_signature(frame, source=str(source), symbol=str(state.get("symbol", "XAUUSD")), timeframe=str(state.get("timeframe", "M1")))
        old_signature = state.get("source_data_signature_20260621")
        state["source_data_signature_20260621"] = signature
        state["source_data_quality_20260621"] = quality
        state["last_manual_refresh_20260621"] = time.time()
        state["last_manual_refresh_message_20260621"] = str(message)
        state["dependent_calculations_stale_20260621"] = bool(ok and signature != old_signature)
        state["canonical_display_stale_20260621"] = bool(ok and signature != old_signature)
        # Explicitly preserve the last completed immutable result.
        if before_canonical is not None:
            state.setdefault("canonical_result_20260617", before_canonical)
        if before_generation is not None:
            state.setdefault("canonical_calculation_generation_20260617", before_generation)
        _clear_source_dependent_presentation(state)
        status = "SUCCESS" if ok and quality["rows"] > 0 else "WARNING" if ok else "FAILURE"
        result = {
            "status": status, "ok": bool(ok), "source": source, "message": message,
            "source_signature": signature, "source_changed": signature != old_signature,
            "calculation_marked_stale": bool(state["dependent_calculations_stale_20260621"]),
            "preserved_generation": before_generation, "quality": quality,
            "wall_seconds": round(time.perf_counter() - started, 4),
        }
    except Exception as exc:
        result = {
            "status": "FAILURE", "ok": False, "message": f"{type(exc).__name__}: {exc}",
            "preserved_generation": before_generation,
            "wall_seconds": round(time.perf_counter() - started, 4),
        }
    state["last_refresh_result_20260621"] = result
    return result


def run_deferred_refresh():
    """Refresh market data only when navigation is not actively switching tabs."""
    nav_age = time.time() - float(st.session_state.get("ui_navigation_click_ts", 0.0) or 0.0)
    if nav_age >= 3.0:
        maybe_refresh(
            st.session_state.get("symbol", "XAUUSD"),
            st.session_state.get("twelve_api_key", ""),
            int(st.session_state.get("refresh_seconds", 600)),
            bridge_url=st.session_state.get("doo_bridge_url", ""),
            bridge_token=st.session_state.get("doo_bridge_token", ""),
        )
    else:
        st.session_state["deferred_auto_refresh_reason"] = "Skipped one auto refresh because user navigation was active."


__all__ = ["refresh_data", "run_deferred_refresh"]
