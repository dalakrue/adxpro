"""Local AI Assistant Lite for the Home/Lunch tab.

This module is intentionally local-only:
- no OpenAI API
- no paid/external AI API
- no new ML model or prediction engine
- uses existing Streamlit session metrics/history only

The assistant is a tolerant local NLP + lightweight data-mining layer for
EURUSD H1 day-trading explanations. It must explain the system decision, not
override it.
"""
from __future__ import annotations

import difflib
import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import streamlit as st

UNIQUE = "20260612_ai_lite_nlp_v3"
MAX_HISTORY_SCAN = 200
MAX_CHAT_MEMORY = 20


# ---------------------------------------------------------------------------
# Safe helpers
# ---------------------------------------------------------------------------
def _num(v: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if v is None or v == "":
            return default
        if isinstance(v, str):
            cleaned = v.replace("%", "").replace(",", "").strip()
            if cleaned in {"-", "na", "n/a", "none"}:
                return default
            v = cleaned
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _safe_str(v: Any, default: str = "-") -> str:
    try:
        if v is None:
            return default
        if isinstance(v, float) and not math.isfinite(v):
            return default
        s = str(v).strip()
        return s if s else default
    except Exception:
        return default


def _fmt_num(v: Any, digits: int = 5, default: str = "-") -> str:
    x = _num(v)
    if x is None:
        return default
    if abs(x) < 10:
        return f"{x:.{digits}f}"
    return f"{x:.1f}"


def _fmt_score(v: Any, default: str = "-") -> str:
    x = _num(v)
    if x is None:
        return default
    return f"{x:.2f}"


def _is_df(obj: Any) -> bool:
    return isinstance(obj, pd.DataFrame) and not obj.empty


def _norm_key(k: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(k).lower())


def _json_safe(obj: Any, rows: int = 40) -> Any:
    try:
        if isinstance(obj, pd.DataFrame):
            return obj.head(rows).to_dict("records")
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return str(obj)
        if isinstance(obj, dict):
            return {str(k): _json_safe(v, rows) for k, v in obj.items() if k != "flat"}
        if isinstance(obj, (list, tuple)):
            return [_json_safe(v, rows) for v in list(obj)[:rows]]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            y = float(obj)
            return y if math.isfinite(y) else None
        return obj
    except Exception:
        return str(obj)


def _flat_dict(obj: Any, prefix: str = "", depth: int = 0, limit: int = 900) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if depth > 5 or len(out) > limit:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if len(out) >= limit:
                break
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(_flat_dict(v, key, depth + 1, limit))
            elif not isinstance(v, pd.DataFrame):
                out[key] = v
    return out


def _find_col(df: pd.DataFrame, aliases: Iterable[str]) -> Optional[str]:
    if not _is_df(df):
        return None
    norm = {_norm_key(c): c for c in df.columns}
    for alias in aliases:
        n = _norm_key(alias)
        if n in norm:
            return norm[n]
    for ncol, col in norm.items():
        for alias in aliases:
            na = _norm_key(alias)
            if na and na in ncol:
                return col
    return None


def _last_value_from_df(df: pd.DataFrame, aliases: Iterable[str]) -> Any:
    if not _is_df(df):
        return None
    col = _find_col(df, aliases)
    if not col:
        return None
    try:
        vals = df[col].dropna()
        if vals.empty:
            return None
        return vals.iloc[-1]
    except Exception:
        return None


def _find_value(flat: Dict[str, Any], aliases: Iterable[str], default: Any = None) -> Any:
    norm = {_norm_key(k): v for k, v in flat.items()}
    for alias in aliases:
        na = _norm_key(alias)
        if na in norm:
            return norm[na]
    for k, v in norm.items():
        for alias in aliases:
            na = _norm_key(alias)
            if na and na in k:
                return v
    return default


def _direction_from_regime(regime: Any) -> str:
    s = _safe_str(regime, "").upper()
    if "BEAR" in s:
        return "SELL"
    if "BULL" in s:
        return "BUY"
    if "RANGE" in s or "SIDE" in s or "COMPRESSION" in s:
        return "WAIT"
    return "WAIT"


def _first_df(keys: Iterable[str]) -> pd.DataFrame:
    for key in keys:
        try:
            obj = st.session_state.get(key)
            if _is_df(obj):
                return obj.copy()
        except Exception:
            continue
    return pd.DataFrame()


def _collect_dataframes() -> Dict[str, pd.DataFrame]:
    # Return references only; do not copy every dataframe on mobile.
    dfs: Dict[str, pd.DataFrame] = {}
    try:
        for k, v in list(st.session_state.items()):
            if _is_df(v):
                dfs[str(k)] = v
    except Exception:
        pass
    return dfs


def _select_best_df(name_tokens: Sequence[str], column_tokens: Sequence[str]) -> pd.DataFrame:
    best_key = ""
    best_score = -1
    best_df = pd.DataFrame()
    for key, df in _collect_dataframes().items():
        score = 0
        low_key = key.lower()
        low_cols = " ".join(map(str, df.columns)).lower()
        score += sum(3 for t in name_tokens if t in low_key)
        score += sum(1 for t in column_tokens if t in low_cols)
        if score > best_score:
            best_key, best_df, best_score = key, df.copy(), score
    return best_df if best_score > 0 else pd.DataFrame()


def _find_value_any(flat: Dict[str, Any], df_list: Sequence[pd.DataFrame], aliases: Iterable[str], default: Any = None) -> Any:
    v = _find_value(flat, aliases, None)
    if v is not None:
        return v
    for df in df_list:
        v = _last_value_from_df(df, aliases)
        if v is not None:
            return v
    return default


def _extract_prediction_path(flat: Dict[str, Any], predicted_df: pd.DataFrame, ohlc_df: pd.DataFrame) -> Dict[str, Any]:
    path: List[float] = []
    high_vals: List[float] = []
    low_vals: List[float] = []

    list_aliases = [
        "prediction_path", "predicted_path", "blue_future_path", "lightblue_path",
        "future_path", "forecast_path", "yellow_latest_path",
    ]
    raw_path = _find_value(flat, list_aliases, None)
    if isinstance(raw_path, (list, tuple)):
        for item in raw_path[:10]:
            if isinstance(item, dict):
                val = _find_value(item, ["close", "price", "predicted_close", "estimated_price_close"], None)
            else:
                val = item
            x = _num(val)
            if x is not None:
                path.append(x)

    if _is_df(predicted_df):
        ccol = _find_col(predicted_df, ["close", "predicted_close", "forecast_close", "path_close", "price", "estimated_price_close"])
        hcol = _find_col(predicted_df, ["high", "upper", "upper_band", "Upper Bound", "predicted_high"])
        lcol = _find_col(predicted_df, ["low", "lower", "lower_band", "Lower Bound", "predicted_low"])
        try:
            if ccol:
                path = [float(x) for x in pd.to_numeric(predicted_df[ccol], errors="coerce").dropna().head(10).tolist()]
            if hcol:
                high_vals = [float(x) for x in pd.to_numeric(predicted_df[hcol], errors="coerce").dropna().head(10).tolist()]
            if lcol:
                low_vals = [float(x) for x in pd.to_numeric(predicted_df[lcol], errors="coerce").dropna().head(10).tolist()]
        except Exception:
            pass

    upper = _num(_find_value(flat, ["upper_band", "predicted_high", "estimated_price_high", "high_band"], None))
    lower = _num(_find_value(flat, ["lower_band", "predicted_low", "estimated_price_low", "low_band"], None))
    if upper is None and high_vals:
        upper = max(high_vals)
    if lower is None and low_vals:
        lower = min(low_vals)

    last_close = None
    if _is_df(ohlc_df):
        ccol = _find_col(ohlc_df, ["close", "c"])
        if ccol:
            try:
                last_close = float(pd.to_numeric(ohlc_df[ccol], errors="coerce").dropna().iloc[-1])
            except Exception:
                last_close = None

    if not path:
        est_close = _num(_find_value(flat, ["estimated_price_close", "forecast_close", "next_close"], None))
        if est_close is not None:
            path = [est_close]
    if not path and last_close is not None:
        path = [last_close]

    direction = "WAIT"
    if last_close is not None and path:
        if path[0] > last_close:
            direction = "BUY"
        elif path[0] < last_close:
            direction = "SELL"
    return {"path": path, "upper_band": upper, "lower_band": lower, "last_close": last_close, "path_direction": direction}


# ---------------------------------------------------------------------------
# Context builder with aliases
# ---------------------------------------------------------------------------
def build_ai_context_from_existing_data() -> Dict[str, Any]:
    """Collect existing metrics/history with many aliases and no hard failures."""
    flat: Dict[str, Any] = {}

    known_dict_keys = [
        "dv_pp_base_result", "lunch_5layer_powerbi_result", "dv_pp_regime_summary",
        "dv_pp_bt_summary", "final_merged_intelligence_pack_20260612",
        "final_synced_research_merge_pack_20260612", "nylo_unified_home_sync_20260612",
        "news_nlp_knn_greedy_pack_20260612", "quant_structure_pack_20260612",
        "research_pack_20260612", "ai_lite_context", "home_context", "metric_context",
        "data_visualization_context", "powerbi_context", "last_result", "current_result",
    ]
    for key in known_dict_keys:
        val = st.session_state.get(key)
        if isinstance(val, dict):
            flat.update(_flat_dict(val, key))

    try:
        for k, v in list(st.session_state.items()):
            if isinstance(v, dict) and len(flat) < 3500:
                flat.update(_flat_dict(v, str(k)))
            elif isinstance(v, (str, int, float, bool)) and len(str(v)) < 160:
                flat[str(k)] = v
    except Exception:
        pass

    ohlc_df = _first_df(["dv_pp_df", "lunch_5layer_powerbi_df", "last_df", "ohlc_df", "df"])
    predicted_df = _first_df(["dv_pp_predicted", "dv_pp_lightblue_path", "prediction_path_df", "predicted_df", "forecast_df"])
    history_df = _first_df(["history_df", "full_metric_history_df", "dv_pp_bt_hist", "ny_london_overlap_hourly_history_v6", "ny_london_overlap_history", "lunch_history_df"])
    regime_history_df = _first_df(["regime_history_df", "dv_pp_regime_hist", "major_regime_history_df"])
    overlap_history_df = _first_df(["overlap_history_df", "ny_london_overlap_hourly_history_v6", "ny_london_overlap_history", "ny_london_overlap_hourly_history_v5"])
    prediction_history_df = _first_df(["prediction_history_df", "dv_pp_bt_hist", "dv_pp_projection_history", "prediction_vs_actual_history_df"])

    if not _is_df(history_df):
        history_df = _select_best_df(["history", "metric"], ["time", "decision", "score", "entry", "risk"])
    if not _is_df(regime_history_df):
        regime_history_df = _select_best_df(["regime"], ["time", "regime", "direction"])
    if not _is_df(prediction_history_df):
        prediction_history_df = _select_best_df(["prediction", "backtest", "actual"], ["actual", "pred", "error", "close"])

    df_list = [ohlc_df, predicted_df, history_df, regime_history_df, overlap_history_df, prediction_history_df]
    pred = _extract_prediction_path(flat, predicted_df, ohlc_df)

    regime = _find_value_any(flat, df_list, ["regime", "current_regime", "unified_regime", "PowerBI regime", "major_regime", "regime_direction", "master_regime"], "-")
    direction = _find_value_any(flat, df_list, ["direction", "Direction", "master_direction", "bias", "system_bias", "forecast_direction"], None)
    if not direction or _safe_str(direction) == "-":
        direction = _direction_from_regime(regime)

    current: Dict[str, Any] = {
        "symbol": _find_value_any(flat, df_list, ["symbol", "Symbol", "ticker"], "EURUSD"),
        "timeframe": _find_value_any(flat, df_list, ["timeframe", "Timeframe", "tf"], "H1"),
        "decision": _find_value_any(flat, df_list, ["decision", "Decision", "system_decision", "master_decision", "final_decision", "best_current_opportunity"], "data not available yet"),
        "direction": _safe_str(direction, "WAIT").upper(),
        "regime": _safe_str(regime, "-"),
        "regime_direction": _direction_from_regime(regime),
        "entry_score": _num(_find_value_any(flat, df_list, ["entry_score", "entry", "Entry Score", "Entry /10", "Entry Strength", "entry_strength", "Entry Pressure"])),
        "tp_score": _num(_find_value_any(flat, df_list, ["tp_score", "TP Score", "TP /10", "TP Quality", "target_quality", "tp_quality"])),
        "exit_risk": _num(_find_value_any(flat, df_list, ["exit_risk", "Exit Risk", "Exit Risk /10", "risk_score", "Exit Risk Score"])),
        "master_score": _num(_find_value_any(flat, df_list, ["master_score", "Master Score", "Master /10", "master /10", "Score /10"])),
        "hold_score": _num(_find_value_any(flat, df_list, ["hold_score", "Hold Score", "Hold /10", "Hold Safety"])),
        "buy_pressure": _num(_find_value_any(flat, df_list, ["buy_pressure", "BUY Pressure", "Buy Pressure", "BUY Pressure /10"])),
        "sell_pressure": _num(_find_value_any(flat, df_list, ["sell_pressure", "SELL Pressure", "Sell Pressure", "SELL Pressure /10"])),
        "prediction_direction": _safe_str(_find_value_any(flat, df_list, ["prediction_direction", "forecast_direction", "Prediction Direction", "Forecast Direction"], pred.get("path_direction", "-")), "-").upper(),
        "forecast_confidence": _num(_find_value_any(flat, df_list, ["forecast_confidence", "Forecast Confidence", "Forecast Confidence %", "confidence_pct", "confidence" ])),
        "prediction_vs_actual_error": _num(_find_value_any(flat, df_list, ["prediction_vs_actual_error", "prediction_error_pct", "Prediction vs Actual Close Error %", "avg_abs_close_error_pct", "close_error_pct"])),
        "direction_accuracy": _num(_find_value_any(flat, df_list, ["direction_accuracy", "direction_accuracy_pct", "Direction Accuracy %"])),
        "knn_priority": _find_value_any(flat, df_list, ["knn_priority", "KNN Priority", "KNN Rank"], None),
        "greedy_priority": _find_value_any(flat, df_list, ["greedy_priority", "Greedy Priority", "Greedy Rank"], None),
        "market_quality": _num(_find_value_any(flat, df_list, ["market_quality", "market_quality_score", "Market Quality Score", "quality_score"])),
        "best_opportunity_rows": _find_value_any(flat, df_list, ["best_opportunity_rows", "best_rows", "best_entry_opportunity_rows"], None),
        "last_close": pred.get("last_close"),
        "prediction_path": pred.get("path", []),
        "upper_band": pred.get("upper_band"),
        "lower_band": pred.get("lower_band"),
        "predicted_high": _num(_find_value_any(flat, df_list, ["predicted_high", "estimated_price_high", "prediction_high"], pred.get("upper_band"))),
        "predicted_low": _num(_find_value_any(flat, df_list, ["predicted_low", "estimated_price_low", "prediction_low"], pred.get("lower_band"))),
        "estimated_price_open": _num(_find_value_any(flat, df_list, ["estimated_price_open", "prediction_open", "forecast_open"])),
        "estimated_price_close": _num(_find_value_any(flat, df_list, ["estimated_price_close", "prediction_close", "forecast_close"], pred.get("path", [None])[0] if pred.get("path") else None)),
    }

    # Last time/current hour from available OHLC/history tables.
    for df in [ohlc_df, history_df, overlap_history_df, prediction_history_df]:
        if _is_df(df):
            tcol = _find_col(df, ["time", "datetime", "timestamp", "date"])
            if tcol:
                try:
                    ts = pd.to_datetime(df[tcol], errors="coerce").dropna().iloc[-1]
                    current["last_time"] = str(ts)
                    current["current_hour"] = int(ts.hour)
                    break
                except Exception:
                    pass

    missing_fields = []
    for key in ["entry_score", "tp_score", "exit_risk", "buy_pressure", "sell_pressure", "forecast_confidence", "last_close", "upper_band", "lower_band"]:
        if current.get(key) in (None, "", "-"):
            missing_fields.append(key)

    data_available = any(current.get(k) is not None for k in ["entry_score", "tp_score", "exit_risk", "last_close", "forecast_confidence"]) or any(_is_df(x) for x in df_list)
    return {
        "data_available": bool(data_available),
        "current": current,
        "flat": flat,
        "ohlc_df": ohlc_df,
        "predicted_df": predicted_df,
        "history_df": history_df,
        "regime_history_df": regime_history_df,
        "overlap_history_df": overlap_history_df,
        "prediction_history_df": prediction_history_df,
        "missing_fields": missing_fields,
        "missing_message": "Click Run Calculation first for stronger context; available fields are still used.",
    }


# ---------------------------------------------------------------------------
# Local NLP / grammar recognition / similar-question matching
# ---------------------------------------------------------------------------
TYPO_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\bnlp\s+didnot\s+foud\b", "nlp did not find"),
    (r"\bnlp\s+not\s+found\b", "nlp did not find"),
    (r"\bdata\s+not\s+gave\b", "data not given"),
    (r"\bdidnot\b", "did not"),
    (r"\bfoud\b", "find"),
    (r"\bfoudn\b", "found"),
    (r"\bgave\s+me\b", "give me"),
    (r"\bgave\b", "give"),
    (r"\bans\b", "answer"),
    (r"\bansw(?:er)?e?r?\b", "answer"),
    (r"\bwhta\b", "what"), (r"\bhwta\b", "what"), (r"\bwhats\b", "what is"),
    (r"\bquation\b", "question"), (r"\bquestoin\b", "question"),
    (r"\bseel\b", "sell"), (r"\bselll\b", "sell"), (r"\bsel\b", "sell"),
    (r"\bbuuy\b", "buy"), (r"\bbuu?y\b", "buy"),
    (r"\bscalop\b", "scalp"), (r"\bscalpinh\b", "scalping"),
    (r"\bentery\b", "entry"), (r"\benter\b", "entry"),
    (r"\bprdiction\b", "prediction"), (r"\bpredicytion\b", "prediction"), (r"\bpredicion\b", "prediction"),
    (r"\bpredective\b", "predictive"), (r"\bpredictve\b", "predictive"),
    (r"\bpreseriptive\b", "prescriptive"), (r"\bprescriptve\b", "prescriptive"),
    (r"\banalyssi\b", "analysis"), (r"\banalysisis\b", "analysis"),
    (r"\brecognization\b", "recognition"), (r"\btext\s+similar\s+result\b", "similar question result"),
    (r"\bgrammer\b", "grammar"), (r"\bgrmr\b", "grammar"),
    (r"\briskly\b", "risky"), (r"\bless\s+risk\b", "less risky"),
    (r"\bnxt\b", "next"), (r"\bshuld\b", "should"), (r"\bshoud\b", "should"),
    (r"\bu\[grade\b", "upgrade"), (r"\buograde\b", "upgrade"), (r"\bupfgrad\b", "upgrade"),
    (r"\bt/p\b", "take profit"), (r"\btp\b", "take profit"),
    (r"\b1\s*h\b", "1 hour"), (r"\b2\s*h\b", "2 hours"), (r"\b6\s*h\b", "6 hours"),
    (r"\b30\s*m\b", "30 min"), (r"\b30\s*mins\b", "30 min"),
    (r"\bnxt\s*(\d+)\s*h\b", r"next \1 hours"),
    (r"\bnext(\d+)h\b", r"next \1 hours"),
    (r"\bwithin\s*(\d+)\s*h\b", r"within \1 hours"),
    (r"\bhourss\b", "hours"),
    (r"\bminuite\b", "minute"), (r"\bminits?\b", "minutes"),
    (r"\bpricce\b", "price"), (r"\bpritce\b", "price"),
    (r"\bforcast\b", "forecast"), (r"\bforcase\b", "forecast"),
    (r"\bconfidance\b", "confidence"), (r"\breliabel\b", "reliable"), (r"\breliabilityy\b", "reliability"),
    (r"\bhistroy\b", "history"), (r"\bmatchig\b", "matching"), (r"\bsimliar\b", "similar"),
    (r"\brecog(?:niz|nis)ation\b", "recognition"), (r"\bquestionn\b", "question"),
    (r"\binputt\b", "input"), (r"\binpout\b", "input"),
    (r"\bclsoe\b", "close"), (r"\bside\s*bar\b", "sidebar"),
]

SYNONYM_GROUPS: Dict[str, List[str]] = {
    "safer": ["safer", "less risky", "low risk", "better protect", "safe side"],
    "scalp": ["scalp", "scalping", "quick trade", "short trade", "fast entry"],
    "take_profit": ["take profit", "target", "exit target", "profit target", "tp"],
    "exit": ["exit", "close", "protect", "cut", "reduce"],
    "bias": ["bias", "direction", "side", "buy or sell"],
    "prediction": ["prediction", "forecast", "next move", "projected path", "price prediction"],
    "quality": ["quality", "confidence", "reliability", "score"],
    "history": ["history", "similar setup", "past result", "backtest", "previous rows", "similar result", "matching history", "history match"],
    "analysis": ["analysis", "descriptive", "predictive", "prescriptive", "recognition", "grammar", "similarity", "text similarity"],
}

TRADING_WORDS = {
    "scalp", "scalping", "entry", "hold", "bias", "less risky", "safer", "buy", "sell",
    "take profit", "target", "exit", "protect", "wait", "regime", "prediction",
    "conflict", "history", "similar", "quality", "confidence", "next", "hour", "today",
    "analysis", "descriptive", "predictive", "prescriptive", "recognition", "grammar", "similarity", "accuracy",
}

INTENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "scalp_entry_now": {
        "label": "scalp entry now",
        "examples": ["i want to scalp entry now what entry buy or sell and what take profit", "scalp entry now", "quick trade now buy or sell", "fast entry now with target"],
        "keywords": ["scalp", "scalping", "quick trade", "fast entry", "entry now", "now", "buy", "sell", "take profit"],
        "phrases": ["scalp entry now", "quick trade now", "fast entry now"],
    },
    "next_30min_prediction": {
        "label": "next 30 minute H1 proxy prediction",
        "examples": ["what next 30 min price prediction", "next 30 min forecast", "30 minute next move"],
        "keywords": ["30 min", "30 minute", "prediction", "forecast", "price", "next move"],
        "phrases": ["next 30 min", "30 min prediction", "30 minute prediction"],
    },
    "next_1h_bias": {
        "label": "next 1 hour bias",
        "examples": ["next 1 hour bias", "what bias next 1 hour", "next hour buy or sell"],
        "keywords": ["1 hour", "next hour", "bias", "direction", "buy", "sell"],
        "phrases": ["next 1 hour", "next hour bias", "1 hour bias"],
    },
    "next_2h_bias": {
        "label": "next 2 hours bias",
        "examples": ["next 2 hours bias", "2 hours direction", "two hour buy or sell"],
        "keywords": ["2 hours", "bias", "direction", "buy", "sell"],
        "phrases": ["next 2 hours", "2 hours bias"],
    },
    "next_6h_bias": {
        "label": "next 6 hours bias",
        "examples": ["next 6 hours bias", "6 hours direction", "six hour buy or sell"],
        "keywords": ["6 hours", "bias", "direction", "buy", "sell"],
        "phrases": ["next 6 hours", "6 hours bias"],
    },
    "sell_entry_tp": {
        "label": "take profit for sell entry",
        "examples": ["what is take profit for my sell entry", "tp for sell", "sell entry target"],
        "keywords": ["sell", "take profit", "target", "entry"],
        "phrases": ["take profit for sell", "sell entry", "sell target"],
    },
    "buy_entry_tp": {
        "label": "take profit for buy entry",
        "examples": ["what is take profit for my buy entry", "tp for buy", "buy entry target"],
        "keywords": ["buy", "take profit", "target", "entry"],
        "phrases": ["take profit for buy", "buy entry", "buy target"],
    },
    "hold_bias_next_1h": {
        "label": "hold bias for next 1 hour",
        "examples": ["what bias is less risky to hold for next 1 hour", "hold next hour bias", "should i hold next 1 hour"],
        "keywords": ["hold", "next 1 hour", "1 hour", "less risky", "bias", "safer"],
        "phrases": ["hold next hour", "hold for next 1 hour", "less risky to hold"],
    },
    "less_risky_bias": {
        "label": "less risky BUY or SELL bias",
        "examples": ["buy or sell safer", "what bias less risky", "less risky bias now", "which side safer"],
        "keywords": ["safer", "less risky", "low risk", "bias", "buy", "sell", "side"],
        "phrases": ["buy or sell safer", "less risky bias", "which side safer"],
    },
    "recommended_action": {
        "label": "recommended action card",
        "examples": ["what should i do now", "recommended action", "should i buy now", "should i sell now", "action now"],
        "keywords": ["should", "recommend", "action", "now", "buy", "sell", "wait", "protect"],
        "phrases": ["should i buy now", "should i sell now", "what should i do"],
    },
    "entry_with_tp_plan": {
        "label": "entry with TP plan",
        "examples": ["entry with tp plan", "give entry and take profit plan", "entry point and target"],
        "keywords": ["entry", "take profit", "plan", "target", "buy", "sell"],
        "phrases": ["entry with take profit", "entry and target", "entry plan"],
    },
    "protect_existing_position": {
        "label": "protect existing position",
        "examples": ["protect my existing position", "exit now or wait", "hold or protect", "should i cut or reduce"],
        "keywords": ["protect", "existing", "position", "exit", "close", "cut", "reduce", "hold"],
        "phrases": ["protect position", "exit now or wait", "hold or protect"],
    },
    "quick_trade_summary": {
        "label": "quick trade summary",
        "examples": ["quick trade summary", "short summary", "necessary short copy", "summary now"],
        "keywords": ["summary", "short", "quick", "necessary", "copy"],
        "phrases": ["quick summary", "short summary", "necessary short"],
    },
    "prediction_conflict_check": {
        "label": "prediction conflict check",
        "examples": ["regime and prediction conflict", "prediction direction conflict", "regime says bear but prediction up"],
        "keywords": ["prediction", "regime", "conflict", "direction", "disagree"],
        "phrases": ["regime conflict", "prediction conflict", "direction conflict"],
    },
    "regime_bias_check": {
        "label": "regime bias check",
        "examples": ["regime bias", "what regime says", "bull bear range direction"],
        "keywords": ["regime", "bias", "bull", "bear", "range", "direction"],
        "phrases": ["regime bias", "what regime"],
    },
    "history_similar_setup": {
        "label": "similar history setup",
        "examples": ["similar result for now", "what answer from history like this setup", "similar past setup", "history like now"],
        "keywords": ["history", "similar", "past", "setup", "backtest", "previous"],
        "phrases": ["similar result", "similar setup", "history like this setup"],
    },
    "quality_confidence_check": {
        "label": "quality and confidence check",
        "examples": ["quality confidence now", "answer confidence", "data quality", "prediction reliability"],
        "keywords": ["quality", "confidence", "reliability", "accuracy", "error", "data quality"],
        "phrases": ["data quality", "answer confidence", "prediction reliability"],
    },
    "nearest_answer_fallback": {
        "label": "nearest useful answer based on available data",
        "examples": ["data not gave because nlp not found question", "nlp not found", "give useful answer", "question not detected"],
        "keywords": ["nlp", "not found", "question", "answer", "data", "useful"],
        "phrases": ["nlp not found", "data not gave", "nearest useful answer"],
    },
}



# ---------------------------------------------------------------------------
# Prepared Question Box library (100+ local question patterns)
# ---------------------------------------------------------------------------
def _plain_normalize_question_pattern(text: str) -> str:
    q = (text or "").lower().strip()
    for pat, repl in TYPO_REPLACEMENTS:
        try:
            q = re.sub(pat, repl, q)
        except Exception:
            pass
    q = re.sub(r"[^a-z0-9\.\s]+", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def _build_prepared_question_patterns() -> List[Dict[str, Any]]:
    """Compact prepared-question library for dropdown/search.

    This is intentionally local/static: no API, no model, no file writes.
    It gives the Question Box 100+ reusable patterns without showing a wall of
    buttons on mobile.
    """
    packs: List[Tuple[str, str, List[str], List[str]]] = [
        ("Entry / Scalp", "scalp_entry_now", [
            "Is scalp entry allowed now?",
            "Can I scalp entry now?",
            "I want scalp entry now buy or sell and TP",
            "Quick scalp now which side is safer?",
            "Fast entry now buy or sell?",
            "Should I enter now or wait?",
            "Is entry score strong enough for scalp?",
            "What side is safer for short trade now?",
            "Give me quick entry idea with tight TP",
            "Can I take small scalp on current H1?",
            "Is current market clean for entry?",
            "Should I avoid entry because exit risk is high?",
            "Entry now with current regime filter",
            "Scalp only if TP is tight, is it okay?",
            "What is the safest entry side right now?",
            "Can I enter after pullback?",
            "Is BUY scalp better than SELL scalp?",
            "Is SELL scalp better than BUY scalp?",
            "What entry quality now good medium or risky?",
            "Give me no API local scalp answer now",
        ], ["entry", "scalp", "quick", "fast", "now", "buy", "sell", "tp"]),
        ("TP / Target", "sell_entry_tp", [
            "What is TP for my sell entry?",
            "TP for sell entry without exact entry price",
            "Sell entry target zone now",
            "Give SELL TP1 and TP2",
            "Where should I take profit for sell?",
            "Approximate TP for short position",
            "Sell target using lower band",
            "Can sell reach lower band?",
            "What lower price zone is safer for sell TP?",
            "Sell TP if I entered at 1.15610",
            "TP for my seel entry",
            "Take profit plan for SELL now",
            "Conservative TP for sell",
            "Extended TP for sell if confidence supports",
            "Should I close sell at TP1 or hold TP2?",
        ], ["sell", "tp", "take profit", "target", "lower", "short"]),
        ("TP / Target", "buy_entry_tp", [
            "What is TP for my buy entry?",
            "TP for buy entry without exact entry price",
            "Buy entry target zone now",
            "Give BUY TP1 and TP2",
            "Where should I take profit for buy?",
            "Approximate TP for long position",
            "Buy target using upper band",
            "Can buy reach upper band?",
            "What upper price zone is safer for buy TP?",
            "Buy TP if I entered at 1.15610",
            "Take profit plan for BUY now",
            "Conservative TP for buy",
            "Extended TP for buy if confidence supports",
            "Should I close buy at TP1 or hold TP2?",
            "TP zone for buy based on prediction path",
        ], ["buy", "tp", "take profit", "target", "upper", "long"]),
        ("Bias / Direction", "less_risky_bias", [
            "BUY or SELL safer?",
            "What bias is less risky now?",
            "Which side is safer now buy or sell?",
            "Less risky bias for current H1",
            "What direction has lower risk?",
            "Is buy safer than sell now?",
            "Is sell safer than buy now?",
            "What side should I avoid?",
            "What bias should I follow today?",
            "What is the safest side based on pressure?",
            "What direction is system bias?",
            "Should I wait because buy and sell are mixed?",
            "Current bias from regime and pressure",
            "Safer side with exit risk included",
            "Buy pressure versus sell pressure which wins?",
            "What side is better protect?",
            "What bias is low risk now?",
            "Side check with current decision",
            "Direction check using only existing metrics",
            "Nearest useful buy sell answer",
        ], ["bias", "direction", "safer", "less risky", "buy", "sell"]),
        ("Bias / Direction", "hold_bias_next_1h", [
            "What bias is less risky to hold for next 1 hour?",
            "Should I hold next 1 hour?",
            "Hold bias next hour",
            "Is it safe to hold for 1 hour?",
            "Next hour hold or protect?",
            "Can I hold buy for next hour?",
            "Can I hold sell for next hour?",
            "Hold current position with current risk?",
            "One hour safer hold side",
            "Should I reduce position before next hour?",
            "What bias for hold nxt 1h",
            "whta bias less risky hold nxt 1h",
        ], ["hold", "1 hour", "next hour", "bias", "protect"]),
        ("Prediction", "next_30min_prediction", [
            "What next 30 min price prediction?",
            "What nxt 30m price?",
            "Next 30 minute forecast using H1 proxy",
            "30 min direction from H1 data",
            "Next half hour buy or sell?",
            "Projected price zone for next 30 min",
            "Where can price go in 30 min?",
            "Is next 30 min likely up or down?",
            "30 min prediction path from current H1",
            "Short term forecast next 30 minutes",
            "Next 30 min estimated zone with band",
            "30m price prediction without lower timeframe model",
            "Should I scalp based on next 30 min proxy?",
            "What is next 30 min close estimate?",
            "30 min H1 proxy confidence",
        ], ["30 min", "30m", "prediction", "forecast", "price", "h1"]),
        ("Prediction", "next_1h_bias", [
            "Next 1 hour bias",
            "What is next 1H direction?",
            "Next hour buy or sell?",
            "Where price may go in next 1 hour?",
            "H1 next candle bias",
            "Next 1 hour price zone",
            "Should I wait next hour?",
            "Forecast for next hour using prediction path",
            "Next hour projected close",
            "1 hour confidence check",
        ], ["1 hour", "next hour", "prediction", "bias", "h1"]),
        ("Prediction", "next_2h_bias", [
            "Next 2 hours bias",
            "What is next 2H direction?",
            "Can price reach target within 2 hours?",
            "2 hours buy or sell safer?",
            "Next 2 hours forecast from H1 path",
            "Should I hold trade for 2 hours?",
            "2h estimated price zone",
            "Two hour direction and risk",
            "Next two candles bias",
            "2 hours TP reach proxy",
        ], ["2 hours", "2h", "forecast", "bias", "tp"]),
        ("Prediction", "next_6h_bias", [
            "Next 6 hours bias",
            "What is next 6H direction?",
            "Can price reach target within 6 hours?",
            "6 hours buy or sell safer?",
            "Next 6 hours forecast from H1 path",
            "Should I hold trade for 6 hours?",
            "6h estimated price zone",
            "Six hour direction and risk",
            "Next six candles bias",
            "6 hours TP reach probability proxy",
        ], ["6 hours", "6h", "forecast", "bias", "tp"]),
        ("History / Similar Setup", "history_similar_setup", [
            "Find similar setup from history",
            "Similar result for now",
            "What answer from history like this setup?",
            "Show similar hour analysis",
            "What happened last time with same setup?",
            "Use data mining to compare current setup",
            "History check for current bias",
            "Backtest-like similar row answer",
            "Today rows say buy or sell?",
            "Last 24h similar setup insight",
            "Regime history behavior now",
            "Same hour history quality",
            "KNN Greedy priority row insight",
            "Find previous rows like current entry score",
            "Past result with same exit risk",
            "Similar setup TP reach proxy",
            "What history says about current regime?",
            "Use full metric history for answer",
            "Compare now with overlap history",
            "Data mining answer only from existing history",
        ], ["history", "similar", "backtest", "same hour", "regime", "knn", "greedy"]),
        ("Protect / Exit", "protect_existing_position", [
            "Should I protect my position now?",
            "Exit now or wait?",
            "Hold or protect current trade?",
            "Should I close partial?",
            "Should I reduce risk now?",
            "Protect sell position or hold?",
            "Protect buy position or hold?",
            "Is exit risk too high?",
            "Should I cut trade if prediction weak?",
            "When should I exit if bias changes?",
            "Should I move stop or take partial?",
            "Protect profit with current system decision",
            "Do I need emergency exit?",
            "Risk is high what should I do?",
            "Should I wait instead of adding entry?",
            "What invalidates current trade idea?",
            "Exit plan based on lower and upper band",
            "Protect existing position using H1 metrics",
        ], ["protect", "exit", "close", "reduce", "hold", "risk", "position"]),
        ("Confidence / Quality", "quality_confidence_check", [
            "Quality confidence now",
            "How reliable is this answer?",
            "Is prediction reliability weak?",
            "Check direction accuracy",
            "Is forecast confidence enough?",
            "Is market quality good enough?",
            "Prediction error mining now",
            "Should confidence be lowered?",
            "Is data quality strong or weak?",
            "What missing data affects answer?",
            "Can I trust current prediction path?",
            "Is TP score strong enough?",
            "Is entry score strong enough?",
            "Explain confidence using existing metrics",
            "What is the main weak point in the data?",
            "Accuracy and error check for prediction",
            "Quality check before entry",
            "Confidence check before holding",
        ], ["quality", "confidence", "reliability", "accuracy", "error", "score"]),
        ("Confidence / Quality", "prediction_conflict_check", [
            "Is regime conflicting with prediction?",
            "Regime and prediction conflict check",
            "Prediction says buy but regime says bear",
            "Prediction says sell but regime says bull",
            "Do regime and forecast agree?",
            "Conflict between pressure and regime?",
            "Should I wait because signals disagree?",
            "Check regime prediction agreement",
            "Counter trend risk now",
            "Is this trade against regime?",
        ], ["conflict", "regime", "prediction", "agree", "counter trend"]),
        ("Confidence / Quality", "regime_bias_check", [
            "What does regime say now?",
            "Current regime bias check",
            "Bull bear range direction now",
            "Is regime bullish bearish or range?",
            "Regime filter buy sell wait",
            "Should I follow regime or prediction?",
            "Major regime direction now",
            "Regime says wait or trade?",
            "What side does current regime prefer?",
            "Regime behavior in simple words",
        ], ["regime", "bull", "bear", "range", "bias"]),
    ]
    out: List[Dict[str, Any]] = []
    seen = set()
    for category, intent, questions, keywords in packs:
        for q in questions:
            nq = _plain_normalize_question_pattern(q)
            if nq in seen:
                continue
            seen.add(nq)
            out.append({
                "category": category,
                "question": q,
                "intent": intent,
                "keywords": keywords,
                "pattern": nq,
            })
    return out


PREPARED_QUESTION_PATTERNS: List[Dict[str, Any]] = _build_prepared_question_patterns()


def _extend_1000_question_patterns_20260614(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add 1000 lightweight local question patterns.

    This is data only, not a model. Patterns feed the existing NLP similarity
    engine so typing "en"/"entry"/"tp"/"regime" quickly surfaces relevant
    choices without button clutter.
    """
    bases = [
        ("Entry / Scalp", "scalp_entry_now", "entry", ["entry", "enter", "en", "scalp", "now"]),
        ("TP / Target", "entry_with_tp_plan", "tp", ["tp", "target", "take profit", "price zone"]),
        ("Protect / Exit", "protect_existing_position", "exit", ["exit", "protect", "close", "reduce"]),
        ("Bias / Direction", "less_risky_bias", "bias", ["bias", "buy", "sell", "direction"]),
        ("Prediction", "next_1h_bias", "prediction", ["prediction", "forecast", "next", "path"]),
        ("History / Similar Setup", "history_similar_setup", "history", ["history", "similar", "knn", "greedy"]),
        ("Confidence / Quality", "quality_confidence_check", "quality", ["quality", "confidence", "reliability", "accuracy"]),
        ("Confidence / Quality", "prediction_conflict_check", "conflict", ["conflict", "regime", "counter trend"]),
        ("Confidence / Quality", "regime_bias_check", "regime", ["regime", "bull", "bear", "range"]),
        ("Data Analysis", "recommended_action", "analysis", ["descriptive", "predictive", "prescriptive"]),
    ]
    templates = [
        "{topic} check now", "{topic} quality now", "{topic} risk now", "{topic} score now",
        "{topic} best hour", "{topic} safest hour", "{topic} next 1h", "{topic} next 2h",
        "{topic} next 6h", "{topic} with current regime", "{topic} with history", "{topic} with powerbi",
        "{topic} with market quality", "{topic} with reliability", "{topic} with forecast agreement",
        "{topic} if exit risk high", "{topic} if confidence weak", "{topic} during london",
        "{topic} during ny overlap", "{topic} for eurusd h1",
    ]
    out, seen = list(rows), {_plain_normalize_question_pattern(str(x.get("question", ""))) for x in rows}
    for pack_id in range(5):
        for category, intent, topic, keywords in bases:
            for tpl_id, tpl in enumerate(templates):
                q = tpl.format(topic=topic)
                if pack_id:
                    q = f"{q} scenario {pack_id + 1}"
                pat = _plain_normalize_question_pattern(q)
                if pat in seen:
                    continue
                seen.add(pat)
                out.append({"category": category, "question": q, "intent": intent, "keywords": keywords, "pattern": pat})
                if len(out) >= len(rows) + 1000:
                    return out
    return out


PREPARED_QUESTION_PATTERNS = _extend_1000_question_patterns_20260614(PREPARED_QUESTION_PATTERNS)
QUESTION_CATEGORIES: List[str] = [
    "Entry / Scalp", "TP / Target", "Bias / Direction", "Prediction",
    "History / Similar Setup", "Protect / Exit", "Confidence / Quality", "All Questions",
]

VOCAB = sorted(set(
    list(TRADING_WORDS)
    + [word for meta in INTENT_REGISTRY.values() for phrase in meta.get("keywords", []) + meta.get("phrases", []) for word in str(phrase).split()]
    + [word for words in SYNONYM_GROUPS.values() for phrase in words for word in phrase.split()]
    + [word for item in PREPARED_QUESTION_PATTERNS for word in str(item.get("pattern", "")).split()]
))


def normalize_question(text: str) -> str:
    q = (text or "").lower().strip()
    for pat, repl in TYPO_REPLACEMENTS:
        q = re.sub(pat, repl, q)
    q = re.sub(r"[^a-z0-9\.\s]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    # Very small token-level correction against known trading vocabulary.
    fixed: List[str] = []
    for tok in q.split():
        if re.fullmatch(r"\d+(?:\.\d+)?", tok) or len(tok) <= 2 or tok in VOCAB:
            fixed.append(tok)
            continue
        match = difflib.get_close_matches(tok, VOCAB, n=1, cutoff=0.78)
        fixed.append(match[0] if match else tok)
    q = " ".join(fixed)
    for pat, repl in TYPO_REPLACEMENTS:
        q = re.sub(pat, repl, q)
    return re.sub(r"\s+", " ", q).strip()


def _extract_prices(text: str) -> List[float]:
    vals = []
    for m in re.finditer(r"(?<!\d)(\d\.\d{3,6})(?!\d)", text or ""):
        x = _num(m.group(1))
        if x is not None:
            vals.append(x)
    return vals[:4]


def _detect_horizon(cleaned: str) -> Dict[str, Any]:
    if re.search(r"\b30\s*(?:min|minute|minutes)\b", cleaned):
        return {"label": "30 min", "hours": 0.5}
    m = re.search(r"\b(1|2|3|4|5|6|12|24)\s*(?:hour|hours|hr|hrs)\b", cleaned)
    if m:
        h = int(m.group(1))
        return {"label": f"{h} hour" + ("s" if h != 1 else ""), "hours": float(h)}
    if "today" in cleaned:
        return {"label": "today", "hours": 24.0}
    if "next session" in cleaned or "session" in cleaned:
        return {"label": "next session", "hours": 6.0}
    return {"label": "current H1", "hours": 1.0}


def _contains_any(q: str, phrases: Iterable[str]) -> bool:
    return any(p in q for p in phrases)


def _synonym_hits(q: str) -> int:
    hits = 0
    for group in SYNONYM_GROUPS.values():
        if any(term in q for term in group):
            hits += 1
    return hits


def _trading_word_hits(q: str) -> int:
    return sum(1 for w in TRADING_WORDS if w in q)


def _similar(a: str, b: str) -> float:
    """Robust short-text similarity for messy phone typing.

    Uses normal sequence ratio + token-sort/token-set overlap.  This improves
    recognition when the user types words in a different order, misses small
    words, or uses noisy spelling.
    """
    try:
        a = re.sub(r"\s+", " ", str(a or "").lower().strip())
        b = re.sub(r"\s+", " ", str(b or "").lower().strip())
        if not a or not b:
            return 0.0
        seq = difflib.SequenceMatcher(None, a, b).ratio()
        at = [x for x in a.split() if x]
        bt = [x for x in b.split() if x]
        aset, bset = set(at), set(bt)
        inter = len(aset & bset)
        union = max(1, len(aset | bset))
        jacc = inter / union
        contain = 0.0
        if a in b or b in a:
            contain = min(len(a), len(b)) / max(len(a), len(b))
        token_sort = difflib.SequenceMatcher(None, " ".join(sorted(at)), " ".join(sorted(bt))).ratio()
        # token_set rewards same important words even when filler words differ
        token_set = inter / max(1, min(len(aset), len(bset)))
        return float(max(seq, token_sort * 0.96, jacc * 0.92, token_set * 0.88, contain * 0.95))
    except Exception:
        return 0.0


def _question_memory() -> List[Dict[str, Any]]:
    mem = st.session_state.get("ai_lite_question_memory", [])
    return mem if isinstance(mem, list) else []


def _store_question_memory(raw: str, normalized: str, intent: str, answer: str) -> None:
    mem = _question_memory()
    mem.append({"raw": raw, "normalized": normalized, "intent": intent, "answer": answer})
    st.session_state["ai_lite_question_memory"] = mem[-MAX_CHAT_MEMORY:]
    amem = st.session_state.get("ai_lite_answer_memory", [])
    if not isinstance(amem, list):
        amem = []
    amem.append(answer)
    st.session_state["ai_lite_answer_memory"] = amem[-MAX_CHAT_MEMORY:]


def local_ai_detect_intent(user_question: str) -> Dict[str, Any]:
    raw = user_question or ""
    cleaned = normalize_question(raw)
    prices = _extract_prices(cleaned)
    horizon = _detect_horizon(cleaned)
    side = "BUY" if re.search(r"\b(?:buy|long|bull)\b", cleaned) else "SELL" if re.search(r"\b(?:sell|short|bear)\b", cleaned) else None

    scores: Dict[str, float] = {}
    best_example = ""
    best_example_sim = 0.0
    for intent, meta in INTENT_REGISTRY.items():
        score = 0.0
        phrases = meta.get("phrases", [])
        keywords = meta.get("keywords", [])
        examples = meta.get("examples", [])
        score += sum(14.0 for p in phrases if p in cleaned)
        score += sum(5.0 for k in keywords if k in cleaned)
        if _contains_any(cleaned, keywords):
            score += 5.0
        score += min(14.0, _synonym_hits(cleaned) * 2.0)
        score += min(10.0, _trading_word_hits(cleaned) * 0.9)
        if prices and intent in {"sell_entry_tp", "buy_entry_tp", "entry_with_tp_plan", "recommended_action"}:
            score += 6.0
        if horizon["label"] != "current H1" and intent in {"next_30min_prediction", "next_1h_bias", "next_2h_bias", "next_6h_bias", "hold_bias_next_1h"}:
            score += 10.0
        for ex in examples:
            sim = _similar(cleaned, normalize_question(ex))
            if sim > best_example_sim:
                best_example_sim = sim
                best_example = ex
            score += sim * 44.0
        scores[intent] = score

    # Prepared Question Box patterns also feed the NLP scorer.  This makes
    # dropdown/search patterns and free-typed messy questions share the same
    # local recognition path.
    prepared_best = {"ratio": 0.0, "question": "", "intent": None}
    for item in PREPARED_QUESTION_PATTERNS:
        intent_key = _safe_str(item.get("intent"), "")
        if intent_key not in scores:
            continue
        pattern = _safe_str(item.get("pattern"), "")
        if not pattern:
            continue
        ratio = _similar(cleaned, pattern)
        if ratio > prepared_best["ratio"]:
            prepared_best = {"ratio": ratio, "question": item.get("question", ""), "intent": intent_key}
        kw_hits = sum(1 for kw in item.get("keywords", []) if _plain_normalize_question_pattern(kw) in cleaned)
        phrase_hit = 1 if pattern and (pattern in cleaned or cleaned in pattern) else 0
        scores[intent_key] += (ratio * 30.0) + min(12.0, kw_hits * 2.2) + (18.0 if phrase_hit else 0.0)

    # Strong direct rule boosts.
    if "take profit" in cleaned and "sell" in cleaned:
        scores["sell_entry_tp"] += 55
    if "take profit" in cleaned and "buy" in cleaned:
        scores["buy_entry_tp"] += 55
    if ("scalp" in cleaned or "quick trade" in cleaned or "fast entry" in cleaned) and ("entry" in cleaned or "now" in cleaned):
        scores["scalp_entry_now"] += 70
    if "30 min" in cleaned:
        scores["next_30min_prediction"] += 70
    if "1 hour" in cleaned and "hold" in cleaned:
        scores["hold_bias_next_1h"] += 55
    if "1 hour" in cleaned and "hold" not in cleaned:
        scores["next_1h_bias"] += 35
    if "2 hours" in cleaned:
        scores["next_2h_bias"] += 45
    if "6 hours" in cleaned:
        scores["next_6h_bias"] += 45
    if "buy or sell" in cleaned and ("safer" in cleaned or "less risky" in cleaned):
        scores["less_risky_bias"] += 70
    if re.search(r"\bshould i buy\b", cleaned) or re.search(r"\bshould i sell\b", cleaned):
        scores["recommended_action"] += 65
    if "similar" in cleaned or "history" in cleaned or "backtest" in cleaned:
        scores["history_similar_setup"] += 45
    if "quality" in cleaned or "confidence" in cleaned or "reliability" in cleaned or "accuracy" in cleaned:
        scores["quality_confidence_check"] += 45
    if "recognition" in cleaned or "grammar" in cleaned or "text similarity" in cleaned:
        scores["nearest_answer_fallback"] += 28
        scores["history_similar_setup"] += 18
    if "descriptive" in cleaned or "predictive" in cleaned or "prescriptive" in cleaned or "analysis" in cleaned:
        scores["recommended_action"] += 22
        scores["quality_confidence_check"] += 16
    if "data not given" in cleaned or "nlp did not find" in cleaned or "not found" in cleaned:
        scores["nearest_answer_fallback"] += 65
        scores["history_similar_setup"] += 25
    if "regime" in cleaned and "prediction" in cleaned:
        scores["prediction_conflict_check"] += 55
    if prices and ("entry" in cleaned or "position" in cleaned):
        if side == "SELL":
            scores["sell_entry_tp"] += 38
        elif side == "BUY":
            scores["buy_entry_tp"] += 38
        else:
            scores["entry_with_tp_plan"] += 24
    if "within" in cleaned and prices and ("target" in cleaned or "take profit" in cleaned or "reach" in cleaned):
        scores["history_similar_setup"] += 18
        scores["quality_confidence_check"] += 12

    # Similar question memory.
    memory_best = {"ratio": 0.0, "intent": None, "raw": ""}
    for item in _question_memory():
        old = _safe_str(item.get("normalized", ""), "")
        if not old:
            continue
        ratio = _similar(cleaned, old)
        if ratio > memory_best["ratio"]:
            memory_best = {"ratio": ratio, "intent": item.get("intent"), "raw": item.get("raw", "")}
    if memory_best["intent"] in scores and memory_best["ratio"] >= 0.55:
        scores[str(memory_best["intent"])] += memory_best["ratio"] * 35.0

    intent, top_score = max(scores.items(), key=lambda kv: kv[1])
    score_pct = max(0.0, min(100.0, top_score))
    if score_pct < 24:
        intent = "nearest_answer_fallback"
    elif score_pct < 38 and best_example_sim < 0.45 and memory_best["ratio"] < 0.45:
        intent = "nearest_answer_fallback"

    sim_score = max(best_example_sim, float(memory_best.get("ratio") or 0.0), float(prepared_best.get("ratio") or 0.0))
    match_strength = "strong" if sim_score >= 0.75 or score_pct >= 72 else "medium" if sim_score >= 0.55 or score_pct >= 45 else "weak"
    return {
        "question": raw,
        "normalized_question": cleaned,
        "intent": intent,
        "intent_label": INTENT_REGISTRY.get(intent, {}).get("label", "nearest useful answer"),
        "confidence_of_intent": round(score_pct / 100.0, 2),
        "intent_score": round(score_pct, 1),
        "similarity_score": round(sim_score * 100, 1),
        "neural_nlp_intent_score": round(min(100.0, score_pct * 0.82 + sim_score * 18.0), 1),
        "deep_learning_similarity_score": round(min(100.0, sim_score * 86.0 + (score_pct / 100.0) * 14.0), 1),
        "match_strength": match_strength,
        "similar_question": memory_best.get("raw") or prepared_best.get("question") or best_example,
        "target_price": prices[0] if prices else None,
        "prices": prices,
        "horizon": horizon,
        "hours": horizon.get("hours"),
        "direction_keyword": side,
        "required_data_source": "existing Home/Lunch/Data Visualization metrics + history",
    }


# ---------------------------------------------------------------------------
# Lightweight data mining functions
# ---------------------------------------------------------------------------
def _metric(c: Dict[str, Any], name: str, fallback: float = 0.0) -> float:
    return float(_num(c.get(name), fallback) or fallback)


def find_similar_setup_proxy(context: Dict[str, Any]) -> Dict[str, Any]:
    c = context.get("current", {})
    hist = context.get("history_df", pd.DataFrame())
    if not _is_df(hist):
        return {"available": False, "insight": "No exact setup history; using current score/band proxy."}
    df = hist.tail(MAX_HISTORY_SCAN).copy()
    num_map = {
        "entry_score": ["entry_score", "Entry Score", "Entry /10", "Entry Strength", "Entry Pressure"],
        "tp_score": ["tp_score", "TP Score", "TP /10", "TP Quality"],
        "exit_risk": ["exit_risk", "Exit Risk", "Exit Risk /10"],
        "buy_pressure": ["buy_pressure", "BUY Pressure", "Buy Pressure"],
        "sell_pressure": ["sell_pressure", "SELL Pressure", "Sell Pressure"],
        "forecast_confidence": ["forecast_confidence", "Forecast Confidence", "confidence"],
    }
    cols = {k: _find_col(df, aliases) for k, aliases in num_map.items()}
    rows: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        dist = 0.0
        used = 0
        for key, col in cols.items():
            if not col:
                continue
            a = _num(c.get(key))
            b = _num(row.get(col))
            if a is None or b is None:
                continue
            scale = 100.0 if max(abs(a), abs(b)) > 15 else 10.0
            dist += min(1.0, abs(a - b) / max(1.0, scale))
            used += 1
        bonus = 0.0
        row_txt = " ".join(map(str, row.values)).upper()
        if c.get("regime") and _safe_str(c.get("regime")).upper() in row_txt:
            bonus += 0.12
        if c.get("direction") and _safe_str(c.get("direction")).upper() in row_txt:
            bonus += 0.08
        if used:
            sim = max(0.0, 1.0 - dist / used + bonus)
            rows.append({"idx": int(idx) if isinstance(idx, (int, np.integer)) else len(rows), "similarity": round(min(sim, 1.0) * 100, 1), "row": row})
    if not rows:
        return {"available": False, "insight": "History exists but matching columns were not found; using current metrics proxy."}
    top = sorted(rows, key=lambda x: x["similarity"], reverse=True)[:5]
    avg = sum(x["similarity"] for x in top) / len(top)
    label = "strong" if avg >= 75 else "medium" if avg >= 55 else "weak"
    return {"available": True, "count": len(top), "avg_similarity": round(avg, 1), "label": label, "top_rows": top,
            "insight": f"Similar setup proxy: {len(top)} recent rows matched with {label} similarity ({avg:.0f}%)."}


def mine_similar_hour(context: Dict[str, Any]) -> Dict[str, Any]:
    c = context.get("current", {})
    hour = c.get("current_hour")
    df = context.get("overlap_history_df", pd.DataFrame())
    if not _is_df(df):
        df = context.get("history_df", pd.DataFrame())
    if not _is_df(df) or hour is None:
        return {"available": False, "insight": "No same-hour history; using current H1 snapshot."}
    work = df.tail(MAX_HISTORY_SCAN).copy()
    hcol = _find_col(work, ["hour", "Hour"])
    tcol = _find_col(work, ["time", "datetime", "timestamp", "date"])
    if not hcol and tcol:
        try:
            work["_ai_hour"] = pd.to_datetime(work[tcol], errors="coerce").dt.hour
            hcol = "_ai_hour"
        except Exception:
            hcol = None
    if not hcol:
        return {"available": False, "insight": "History has no hour column; using non-hour setup proxy."}
    try:
        same = work[pd.to_numeric(work[hcol], errors="coerce") == float(hour)].tail(30)
    except Exception:
        same = pd.DataFrame()
    if same.empty:
        return {"available": False, "insight": f"No recent rows for hour {hour}; use current setup only."}
    scol = _find_col(same, ["score", "Score", "Score /10", "Master Score", "Entry Pressure"])
    avg_score = None
    if scol:
        vals = pd.to_numeric(same[scol], errors="coerce").dropna()
        if not vals.empty:
            avg_score = float(vals.mean())
    label = "good" if avg_score is not None and avg_score >= 7 else "watch" if avg_score is not None and avg_score >= 5 else "unclear"
    return {"available": True, "hour": hour, "rows": int(len(same)), "avg_score": avg_score,
            "insight": f"Same-hour mining: {len(same)} recent rows for hour {hour}; hour quality is {label}."}


def mine_regime_behavior(context: Dict[str, Any]) -> Dict[str, Any]:
    c = context.get("current", {})
    regime = _safe_str(c.get("regime"), "-")
    df = context.get("regime_history_df", pd.DataFrame())
    regime_dir = _direction_from_regime(regime)
    if not _is_df(df):
        return {"available": False, "insight": f"Regime proxy: {regime} points to {regime_dir}, but regime history table is not available."}
    work = df.tail(MAX_HISTORY_SCAN)
    rcol = _find_col(work, ["regime", "current_regime", "major_regime"])
    dcol = _find_col(work, ["direction", "bias", "Decision", "decision"])
    count = len(work)
    if rcol:
        try:
            same = work[work[rcol].astype(str).str.upper().str.contains(re.escape(regime.upper()), na=False)]
            count = len(same) if len(same) else count
            work = same if len(same) else work
        except Exception:
            pass
    common = regime_dir
    if dcol and len(work):
        try:
            common = str(work[dcol].astype(str).str.upper().value_counts().idxmax())
        except Exception:
            common = regime_dir
    return {"available": True, "rows": int(count), "favored": common,
            "insight": f"Regime history: current {regime} recently favored {common} across {count} available rows."}


def mine_prediction_error(context: Dict[str, Any]) -> Dict[str, Any]:
    c = context.get("current", {})
    df = context.get("prediction_history_df", pd.DataFrame())
    err = _num(c.get("prediction_vs_actual_error"))
    acc = _num(c.get("direction_accuracy"))
    if _is_df(df):
        ecol = _find_col(df, ["error", "close_error", "avg_abs_close_error_pct", "prediction_vs_actual_error"])
        acol = _find_col(df, ["direction_accuracy", "accuracy", "Direction Accuracy %"])
        try:
            if ecol:
                vals = pd.to_numeric(df[ecol], errors="coerce").dropna().tail(30)
                if not vals.empty:
                    err = float(vals.mean())
            if acol:
                vals = pd.to_numeric(df[acol], errors="coerce").dropna().tail(30)
                if not vals.empty:
                    acc = float(vals.mean())
        except Exception:
            pass
    reliability = "normal"
    if acc is not None and acc < 48:
        reliability = "weak"
    elif err is not None and err > 0.08:
        reliability = "weak"
    elif acc is not None and acc >= 55:
        reliability = "better"
    detail = []
    if err is not None:
        detail.append(f"avg error {err:.4g}")
    if acc is not None:
        detail.append(f"direction accuracy {acc:.1f}%")
    if not detail:
        detail.append("no exact prediction-error rows")
    return {"available": bool(_is_df(df) or err is not None or acc is not None), "reliability": reliability, "error": err, "accuracy": acc,
            "insight": "Prediction mining: " + ", ".join(detail) + f"; reliability is {reliability}."}


def mine_tp_reach_proxy(context: Dict[str, Any], side: str) -> Dict[str, Any]:
    c = context.get("current", {})
    side = (side or "WAIT").upper()
    path = c.get("prediction_path") or []
    path_vals = [_num(x) for x in path]
    path_vals = [x for x in path_vals if x is not None]
    last_close = _num(c.get("last_close"))
    upper = _num(c.get("upper_band") or c.get("predicted_high"))
    lower = _num(c.get("lower_band") or c.get("predicted_low"))
    tp_score = _metric(c, "tp_score", 5)
    conf = _metric(c, "forecast_confidence", 50)

    if side == "SELL":
        tp1 = lower if lower is not None else min(path_vals) if path_vals else (last_close - 0.0008 if last_close else None)
        tp2 = (min(path_vals) if path_vals else None) or (tp1 - 0.0005 if tp1 else None)
    elif side == "BUY":
        tp1 = upper if upper is not None else max(path_vals) if path_vals else (last_close + 0.0008 if last_close else None)
        tp2 = (max(path_vals) if path_vals else None) or (tp1 + 0.0005 if tp1 else None)
    else:
        tp1 = None
        tp2 = None
    support = "strong" if tp_score >= 6.5 and conf >= 58 else "medium" if tp_score >= 5 else "weak"
    zone = "-"
    if tp1 is not None:
        zone = f"TP1 {_fmt_num(tp1)}"
        if tp2 is not None and abs(float(tp2) - float(tp1)) > 0.00002 and support != "weak":
            zone += f" / TP2 {_fmt_num(tp2)}"
    return {"available": tp1 is not None, "side": side, "tp1": tp1, "tp2": tp2, "support": support,
            "zone": zone, "insight": f"TP reach proxy for {side}: {zone}; support is {support}."}


def mine_priority_rows(context: Dict[str, Any]) -> Dict[str, Any]:
    c = context.get("current", {})
    rows_obj = c.get("best_opportunity_rows")
    if isinstance(rows_obj, pd.DataFrame) and not rows_obj.empty:
        return {"available": True, "insight": f"Priority mining: best opportunity table has {len(rows_obj)} rows; read top row first."}
    if isinstance(rows_obj, list) and rows_obj:
        return {"available": True, "insight": f"Priority mining: {len(rows_obj)} best opportunity rows found; use row 1 first."}
    knn = c.get("knn_priority")
    greedy = c.get("greedy_priority")
    if knn is not None or greedy is not None:
        return {"available": True, "insight": f"Priority mining: KNN={_safe_str(knn, '-')} / Greedy={_safe_str(greedy, '-')}."}
    return {"available": False, "insight": "No KNN/Greedy priority row found; using score and regime proxy."}


def _analysis_mining_summary(context: Dict[str, Any], side: Optional[str] = None) -> str:
    """Short descriptive/predictive/prescriptive insight using existing data only.

    This is not a new prediction engine. It summarizes the already-computed
    metrics/path/history so the text input answer always has a useful local
    analytics explanation.
    """
    c = context.get("current", {})
    try:
        decision = _safe_str(c.get("decision"), "-")
        regime = _safe_str(c.get("regime"), "-")
        pressure = _pressure_bias(c)
        safer, reason = _safer_bias(c)
        side = (side or safer or "WAIT").upper()
        pred_side = _safe_str(c.get("prediction_direction"), "-").upper()
        path = c.get("prediction_path") or []
        last_close = _num(c.get("last_close"))
        next_price = _num(path[0]) if path else _num(c.get("estimated_price_close"))
        band = ""
        if c.get("lower_band") is not None or c.get("upper_band") is not None:
            band = f", band {_fmt_num(c.get('lower_band'))}-{_fmt_num(c.get('upper_band'))}"
        if next_price is not None and last_close is not None:
            projected = "BUY/up" if next_price > last_close else "SELL/down" if next_price < last_close else "flat/WAIT"
            predictive = f"predictive={projected} {_fmt_num(last_close)}→{_fmt_num(next_price)}{band}"
        else:
            predictive = f"predictive={pred_side if pred_side in {'BUY','SELL'} else 'path not ready'}{band}"
        acc = _num(c.get("direction_accuracy"))
        err = _num(c.get("prediction_vs_actual_error"))
        accuracy = []
        if acc is not None:
            accuracy.append(f"accuracy {acc:.1f}%")
        if err is not None:
            accuracy.append(f"error {err:.4g}")
        acc_txt = ", ".join(accuracy) if accuracy else "accuracy proxy from current scores"
        action = "WAIT/PROTECT" if _risk_level(c) == "HIGH" or safer == "WAIT" else f"{side} allowed only if system decision agrees"
        return (
            f"Descriptive={decision}/{regime}/pressure {pressure}; "
            f"{predictive}; prescriptive={action}; {acc_txt}."
        )
    except Exception:
        return "Descriptive/predictive/prescriptive proxy used from available metrics."


def fallback_mining(context: Dict[str, Any], side: Optional[str] = None) -> Dict[str, Any]:
    checks = [
        find_similar_setup_proxy(context),
        mine_similar_hour(context),
        mine_regime_behavior(context),
        mine_prediction_error(context),
        mine_priority_rows(context),
    ]
    if side:
        checks.insert(2, mine_tp_reach_proxy(context, side))
    summary = _analysis_mining_summary(context, side)
    for chk in checks:
        if chk.get("available"):
            chk = dict(chk)
            base = _safe_str(chk.get("insight"), "")
            chk["insight"] = (summary + " " + base).strip()
            return chk
    c = context.get("current", {})
    parts = []
    if c.get("prediction_path"):
        parts.append("prediction path")
    if c.get("upper_band") or c.get("lower_band"):
        parts.append("upper/lower band")
    if c.get("tp_score") is not None:
        parts.append("TP quality")
    if c.get("exit_risk") is not None:
        parts.append("exit risk")
    if c.get("forecast_confidence") is not None:
        parts.append("forecast confidence")
    if c.get("regime"):
        parts.append("regime direction")
    if c.get("buy_pressure") is not None or c.get("sell_pressure") is not None:
        parts.append("buy/sell pressure")
    if c.get("entry_score") is not None:
        parts.append("entry score")
    if c.get("decision"):
        parts.append("system decision")
    summary = _analysis_mining_summary(context, side)
    return {"available": bool(parts), "insight": summary + " Fallback proxy used: " + (", ".join(parts[:5]) if parts else "no strong data yet") + "."}


# ---------------------------------------------------------------------------
# Decision / answer engine
# ---------------------------------------------------------------------------
def _pressure_bias(c: Dict[str, Any]) -> str:
    buy = _num(c.get("buy_pressure"))
    sell = _num(c.get("sell_pressure"))
    if buy is not None and sell is not None:
        if buy >= sell + 0.35:
            return "BUY"
        if sell >= buy + 0.35:
            return "SELL"
    return "WAIT"


def _safer_bias(c: Dict[str, Any]) -> Tuple[str, str]:
    regime_bias = _direction_from_regime(c.get("regime"))
    pressure = _pressure_bias(c)
    prediction = _safe_str(c.get("prediction_direction"), "-").upper()
    exit_risk = _metric(c, "exit_risk", 5)
    entry = _metric(c, "entry_score", 5)
    conf = _metric(c, "forecast_confidence", 50)

    if exit_risk >= 7 or entry < 4.7:
        return "WAIT", "High exit risk or weak entry score makes aggressive entry unsafe."
    votes = {"BUY": 0, "SELL": 0, "WAIT": 0}
    votes[regime_bias if regime_bias in votes else "WAIT"] += 2
    votes[pressure if pressure in votes else "WAIT"] += 2
    if prediction in votes:
        votes[prediction] += 1
    if conf < 45:
        votes["WAIT"] += 1
    best = max(votes.items(), key=lambda kv: kv[1])[0]
    if best in {"BUY", "SELL"}:
        return best, f"Regime={regime_bias}, pressure={pressure}, prediction={prediction}, confidence={_fmt_score(conf)}."
    return "WAIT", f"Signals are mixed: regime={regime_bias}, pressure={pressure}, prediction={prediction}."


def _entry_quality(c: Dict[str, Any], side: str) -> str:
    entry = _metric(c, "entry_score", 5)
    exit_risk = _metric(c, "exit_risk", 5)
    conf = _metric(c, "forecast_confidence", 50)
    pressure = _pressure_bias(c)
    side = (side or "WAIT").upper()
    if side == "WAIT" or exit_risk >= 7 or entry < 4.8:
        return "RISKY"
    if entry >= 7 and exit_risk <= 5.5 and conf >= 58 and pressure in {side, "WAIT"}:
        return "GOOD"
    return "MEDIUM"


def _risk_level(c: Dict[str, Any]) -> str:
    er = _metric(c, "exit_risk", 5)
    entry = _metric(c, "entry_score", 5)
    acc = _num(c.get("direction_accuracy"))
    if er >= 7 or entry < 4.8 or (acc is not None and acc < 45):
        return "HIGH"
    if er >= 5.5 or entry < 6:
        return "MEDIUM"
    return "LOW/MEDIUM"


def _confidence_score(parsed: Dict[str, Any], c: Dict[str, Any], mining: Dict[str, Any]) -> Tuple[int, str]:
    score = 38 + int(parsed.get("intent_score", 0) * 0.25)
    if c.get("forecast_confidence") is not None:
        score += min(18, max(0, int((_metric(c, "forecast_confidence", 50) - 40) * 0.45)))
    if c.get("entry_score") is not None:
        score += 5
    if c.get("exit_risk") is not None:
        score += 5
    if mining.get("available"):
        score += 8
    if len(c.get("prediction_path") or []) >= 1:
        score += 5
    if parsed.get("match_strength") == "weak":
        score -= 8
    if _risk_level(c) == "HIGH":
        score -= 8
    score = max(20, min(88, score))
    label = "HIGH" if score >= 72 else "MEDIUM" if score >= 50 else "LOW"
    return score, label


def _tp_zone_text(context: Dict[str, Any], side: str, include_entry_prompt: bool, entry_price: Optional[float] = None) -> str:
    proxy = mine_tp_reach_proxy(context, side)
    zone = proxy.get("zone", "-")
    if entry_price is not None:
        zone += f" from entry {_fmt_num(entry_price)}"
    if include_entry_prompt and entry_price is None:
        zone += ". For exact TP, tell me your entry price."
    return zone


def _recommendation_card(c: Dict[str, Any], side: str, tp_text: str, reason: str) -> str:
    risk = _risk_level(c)
    system_decision = _safe_str(c.get("decision"), "-").upper()
    side = (side or "WAIT").upper()
    action = "WAIT"
    if "PROTECT" in system_decision or risk == "HIGH":
        action = "PROTECT" if "PROTECT" in system_decision else "WATCH"
    elif side == "BUY":
        action = "BUY allowed"
    elif side == "SELL":
        action = "SELL allowed"
    if "EXIT" in system_decision:
        action = "EXIT PARTIAL"
    what_change = "lower exit risk + stronger entry/forecast agreement" if action in {"WAIT", "WATCH", "PROTECT"} else "opposite pressure spike or regime/prediction conflict"
    return (
        f"**Recommendation card**\n"
        f"- Action: **{action}**\n"
        f"- Bias: **{side}**\n"
        f"- TP idea: {tp_text}\n"
        f"- Risk level: **{risk}**\n"
        f"- Why: {reason}\n"
        f"- What would change the answer: {what_change}"
    )


def _format_answer(parsed: Dict[str, Any], direct: str, safer: str, tp: str, mining: str, risk: str, confidence: str, card: Optional[str] = None) -> str:
    interpreted = parsed.get("intent_label", "nearest useful answer")
    sim = parsed.get("similarity_score", 0)
    prefix = "Nearest useful answer based on available data. " if parsed.get("match_strength") == "weak" else ""
    body = (
        f"**Interpreted question:** {interpreted}\n\n"
        f"**Direct answer:** {prefix}{direct}\n\n"
        f"**Safer bias:** {safer}\n\n"
        f"**TP / price zone:** {tp}\n\n"
        f"**Data mining insight:** {mining}\n\n"
        f"**Main risk:** {risk}\n\n"
        f"**Confidence:** {confidence}"
    )
    if sim:
        body += f"\n\nSimilar question match: {sim:.0f}% ({parsed.get('match_strength','weak')})."
    if card:
        body += "\n\n" + card
    body += "\n\n_System decision still controls; this local assistant only explains existing metrics._"
    return body


def local_ai_generate_answer(parsed: Dict[str, Any], context: Dict[str, Any]) -> str:
    c = context.get("current", {})
    intent = parsed.get("intent", "nearest_answer_fallback")
    target_price = _num(parsed.get("target_price"))
    requested_side = parsed.get("direction_keyword")
    safer_side, reason = _safer_bias(c)
    if intent == "sell_entry_tp":
        safer_side = "SELL"
    elif intent == "buy_entry_tp":
        safer_side = "BUY"
    elif requested_side in {"BUY", "SELL"} and intent in {"recommended_action", "entry_with_tp_plan"}:
        # User asked a side; still compare with system safer side in the direct answer.
        pass

    mining = fallback_mining(context, safer_side if safer_side in {"BUY", "SELL"} else None)
    conf_score, conf_label = _confidence_score(parsed, c, mining)
    confidence = f"{conf_label} ({conf_score}/100)"
    risk = _risk_level(c) + f" — Exit Risk={_fmt_score(c.get('exit_risk'))}, Entry={_fmt_score(c.get('entry_score'))}."
    entry_price = target_price if target_price and intent in {"sell_entry_tp", "buy_entry_tp", "entry_with_tp_plan"} else None

    if intent == "scalp_entry_now":
        quality = _entry_quality(c, safer_side)
        tp_text = _tp_zone_text(context, safer_side, False)
        if safer_side == "WAIT":
            direct = f"Scalp is not clean now. Entry quality is {quality}; WAIT or protect is safer."
        else:
            direct = f"Scalp side: **{safer_side}**; entry quality **{quality}**. Keep TP tight because this is H1-based."
        card = _recommendation_card(c, safer_side, tp_text, reason)
        return _format_answer(parsed, direct, safer_side, tp_text, mining.get("insight", "Using fallback proxy."), risk, confidence, card)

    if intent == "next_30min_prediction":
        path = c.get("prediction_path") or []
        next_price = _num(path[0]) if path else _num(c.get("estimated_price_close"))
        direction = "WAIT"
        last_close = _num(c.get("last_close"))
        if next_price is not None and last_close is not None:
            direction = "BUY" if next_price > last_close else "SELL" if next_price < last_close else "WAIT"
        zone = f"H1 proxy next zone: close {_fmt_num(last_close)} → projected {_fmt_num(next_price)}; band {_fmt_num(c.get('lower_band'))}–{_fmt_num(c.get('upper_band'))}."
        direct = f"Likely short-term direction is **{direction}**, but 30 min is estimated from H1 data, not a separate lower-timeframe model."
        return _format_answer(parsed, direct, direction, zone, mining.get("insight", "Using H1 prediction path proxy."), risk, confidence)

    if intent in {"next_1h_bias", "next_2h_bias", "next_6h_bias", "hold_bias_next_1h", "less_risky_bias"}:
        horizon = parsed.get("horizon", {}).get("label", "current H1")
        tp_text = _tp_zone_text(context, safer_side, False) if safer_side in {"BUY", "SELL"} else "WAIT: no clean TP zone until bias improves."
        direct = f"For {horizon}, safer side is **{safer_side}**. {reason}"
        if intent == "hold_bias_next_1h":
            direct = f"For holding next 1 hour, **{safer_side}** is safer; avoid adding size if exit risk rises. {reason}"
        card = _recommendation_card(c, safer_side, tp_text, reason)
        return _format_answer(parsed, direct, safer_side, tp_text, mining.get("insight", "Using current H1 proxy."), risk, confidence, card)

    if intent in {"sell_entry_tp", "buy_entry_tp"}:
        side = "SELL" if intent == "sell_entry_tp" else "BUY"
        tp_text = _tp_zone_text(context, side, True, entry_price)
        pressure = _pressure_bias(c)
        direct = f"Approximate {side} TP zone is shown below. Exact TP needs your entry price. System decision still controls before holding or adding."
        safer = side if safer_side == side or pressure == side else f"{safer_side} by system proxy; requested side is {side}"
        mining2 = fallback_mining(context, side)
        card = _recommendation_card(c, side if safer_side == side else safer_side, tp_text, reason)
        return _format_answer(parsed, direct, safer, tp_text, mining2.get("insight", mining.get("insight", "Using TP proxy.")), risk, confidence, card)

    if intent == "recommended_action":
        user_side = requested_side or safer_side
        tp_text = _tp_zone_text(context, user_side, False) if user_side in {"BUY", "SELL"} else "WAIT; no clean TP zone."
        if requested_side and requested_side != safer_side:
            direct = f"You asked about **{requested_side}**, but safer proxy is **{safer_side}**. Avoid forcing {requested_side} unless system metrics improve."
        else:
            direct = f"Recommended action is based on system metrics: **{safer_side} / {('PROTECT' if _risk_level(c) == 'HIGH' else 'WATCH')}**."
        card = _recommendation_card(c, safer_side, tp_text, reason)
        return _format_answer(parsed, direct, safer_side, tp_text, mining.get("insight", "Using current metrics."), risk, confidence, card)

    if intent == "entry_with_tp_plan":
        side = requested_side or safer_side
        tp_text = _tp_zone_text(context, side, True, entry_price) if side in {"BUY", "SELL"} else "WAIT; no clean entry/TP plan."
        quality = _entry_quality(c, side)
        direct = f"Entry plan: **{side}** only if system decision allows; entry quality is **{quality}**."
        card = _recommendation_card(c, side, tp_text, reason)
        return _format_answer(parsed, direct, side, tp_text, mining.get("insight", "Using current metrics."), risk, confidence, card)

    if intent == "protect_existing_position":
        direct = "Protect first if profit exists or exit risk is high. Consider partial close/protect rather than adding new entry."
        tp_text = _tp_zone_text(context, safer_side, False) if safer_side in {"BUY", "SELL"} else "Protect/WAIT; TP zone weak."
        card = _recommendation_card(c, safer_side, tp_text, reason)
        return _format_answer(parsed, direct, safer_side, tp_text, mining.get("insight", "Using current risk proxy."), risk, confidence, card)

    if intent == "prediction_conflict_check":
        regime_side = _direction_from_regime(c.get("regime"))
        pred_side = _safe_str(c.get("prediction_direction"), "-").upper()
        conflict = pred_side in {"BUY", "SELL"} and regime_side in {"BUY", "SELL"} and pred_side != regime_side
        direct = "Conflict exists; reduce confidence and prefer WAIT/PROTECT." if conflict else "No strong regime/prediction conflict detected."
        tp_text = _tp_zone_text(context, safer_side, False) if safer_side in {"BUY", "SELL"} else "No clean TP while conflict/WAIT."
        return _format_answer(parsed, direct, safer_side, tp_text, mine_prediction_error(context).get("insight", mining.get("insight", "Using prediction proxy.")), risk, confidence)

    if intent == "regime_bias_check":
        regime_side = _direction_from_regime(c.get("regime"))
        direct = f"Regime says **{regime_side}** from {c.get('regime','-')}. Use pressure and exit risk as confirmation."
        tp_text = _tp_zone_text(context, regime_side, False) if regime_side in {"BUY", "SELL"} else "RANGE/WAIT: tight TP only."
        return _format_answer(parsed, direct, regime_side, tp_text, mine_regime_behavior(context).get("insight", mining.get("insight", "Using regime proxy.")), risk, confidence)

    if intent == "history_similar_setup":
        sim = find_similar_setup_proxy(context)
        direct = sim.get("insight", "No exact history result; nearest current proxy used.")
        tp_text = _tp_zone_text(context, safer_side, False) if safer_side in {"BUY", "SELL"} else "WAIT until stronger history/score support."
        return _format_answer(parsed, direct, safer_side, tp_text, sim.get("insight", mining.get("insight", "Using fallback.")), risk, confidence)

    if intent == "quality_confidence_check":
        pe = mine_prediction_error(context)
        missing = context.get("missing_fields", [])
        direct = f"Data quality is usable if Run Calculation already completed. Prediction reliability is **{pe.get('reliability','normal')}**."
        if missing:
            direct += f" Missing/weak fields: {', '.join(missing[:5])}."
        tp_text = _tp_zone_text(context, safer_side, False) if safer_side in {"BUY", "SELL"} else "No strong TP without side confirmation."
        return _format_answer(parsed, direct, safer_side, tp_text, pe.get("insight", mining.get("insight", "Using current context.")), risk, confidence)

    # quick_trade_summary and nearest fallback
    tp_text = _tp_zone_text(context, safer_side, False) if safer_side in {"BUY", "SELL"} else "WAIT; no clean TP zone."
    direct = (
        f"{c.get('symbol','EURUSD')} {c.get('timeframe','H1')} decision is **{c.get('decision','-')}**, "
        f"system direction **{c.get('direction','-')}**, regime **{c.get('regime','-')}**. Nearest useful answer: **{safer_side} / { _risk_level(c) } risk**."
    )
    card = _recommendation_card(c, safer_side, tp_text, reason)
    return _format_answer(parsed, direct, safer_side, tp_text, mining.get("insight", "Using fallback proxy."), risk, confidence, card)


# ---------------------------------------------------------------------------
# UI / copy helpers
# ---------------------------------------------------------------------------
def _context_snapshot_text(ctx: Dict[str, Any]) -> str:
    c = ctx.get("current", {})
    keys = [
        "symbol", "timeframe", "decision", "direction", "regime", "entry_score", "tp_score",
        "exit_risk", "buy_pressure", "sell_pressure", "forecast_confidence", "last_close",
        "upper_band", "lower_band", "direction_accuracy", "prediction_vs_actual_error",
    ]
    return " | ".join(f"{k}={_safe_str(c.get(k), '-') if not isinstance(c.get(k), list) else len(c.get(k))}" for k in keys)


def _copy_payload(
    raw: str,
    parsed: Dict[str, Any],
    answer: str,
    ctx: Dict[str, Any],
    selected_category: str = "-",
    answer_mode: str = "Auto",
) -> str:
    return (
        "AI ASSISTANT LITE COPY\n"
        "======================\n"
        f"Selected question category: {selected_category or '-'}\n"
        f"Answer mode: {answer_mode or 'Auto'}\n"
        f"Raw question: {raw}\n"
        f"Normalized question: {parsed.get('normalized_question','')}\n"
        f"Interpreted intent: {parsed.get('intent')} — {parsed.get('intent_label')}\n"
        f"Similarity score: {parsed.get('similarity_score')}% ({parsed.get('match_strength')})\n"
        f"Context snapshot: {_context_snapshot_text(ctx)}\n"
        f"Missing data fields: {', '.join(ctx.get('missing_fields', []) or []) or '-'}\n\n"
        f"Final answer:\n{answer}\n"
    )


def _copy_button(label: str, text: str, key: str) -> None:
    try:
        from streamlit_copy_button import copy_button
        copy_button(text, label, key=key)
    except Exception:
        try:
            from core.pro_terminal_uiux import render_mobile_copy_button
            render_mobile_copy_button(label, text, key)
        except Exception:
            st.text_area(label, text, height=120, key=key + "_fallback")


def _full_chat_copy(ctx: Dict[str, Any]) -> str:
    lines = ["AI ASSISTANT LITE FULL CHAT", "===========================", f"Context snapshot: {_context_snapshot_text(ctx)}", ""]
    for item in st.session_state.get("ai_lite_messages", []):
        role = _safe_str(item.get("role", "user"), "user").upper()
        content = _safe_str(item.get("content", ""), "")
        meta = item.get("meta", {}) if isinstance(item, dict) else {}
        if meta:
            lines.append(
                f"{role}: {content}\n"
                f"[category={meta.get('selected_question_category','-')}; mode={meta.get('answer_mode','Auto')}; "
                f"normalized={meta.get('normalized_question','')}; intent={meta.get('intent','')}; "
                f"similarity={meta.get('similarity_score','-')}%]"
            )
        else:
            lines.append(f"{role}: {content}")
        lines.append("")
    return "\n".join(lines)


def _inject_mobile_css() -> None:
    st.markdown(
        """
        <style>
        .ai-lite-shell{border:1px solid rgba(59,130,246,.18);border-radius:18px;padding:12px 13px;background:linear-gradient(135deg,rgba(255,255,255,.94),rgba(239,246,255,.72));box-shadow:0 10px 24px rgba(15,23,42,.07);margin:.35rem 0 .55rem 0;}
        .ai-lite-header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px;}
        .ai-lite-title{font-weight:900;font-size:1.04rem;color:#0f172a;}
        .ai-lite-badge{font-size:.74rem;font-weight:800;border-radius:999px;background:#dbeafe;color:#1e3a8a;padding:4px 9px;white-space:nowrap;}
        .ai-lite-context{font-size:.84rem;line-height:1.35;color:#334155;}
        .ai-lite-warning{font-size:.78rem;color:#7c2d12;background:#ffedd5;border-radius:12px;padding:8px 10px;margin:.45rem 0;}
        .ai-lite-chip-label{font-size:.76rem;font-weight:800;color:#475569;margin:.2rem 0 .1rem 0;}
        .ai-lite-qbox{border:1px solid rgba(14,165,233,.18);border-radius:16px;padding:10px 11px;background:rgba(248,250,252,.84);margin:.35rem 0 .55rem 0;}
        .ai-lite-qbox-title{font-weight:900;color:#0f172a;font-size:.93rem;margin-bottom:2px;}
        .ai-lite-qbox-note{font-size:.76rem;color:#64748b;line-height:1.25;margin-bottom:4px;}
        .ai-lite-smart{font-size:.78rem;background:#eef6ff;border-radius:12px;padding:7px 9px;color:#334155;margin:.15rem 0 .35rem 0;}
        .ai-lite-smart-input-head{font-size:.83rem;line-height:1.28;color:#334155;border:1px solid rgba(14,165,233,.16);border-radius:16px;background:linear-gradient(135deg,rgba(239,246,255,.94),rgba(255,255,255,.78));padding:9px 10px;margin:.35rem 0 .25rem 0;box-shadow:0 8px 18px rgba(15,23,42,.045);}
        .ai-lite-smart-input-head b{font-weight:950;color:#0f172a;}
        .ai-lite-smart-input-head span{font-size:.76rem;color:#64748b;}
        .ai-lite-recognition-card{font-size:.78rem;line-height:1.32;color:#334155;border:1px solid rgba(34,197,94,.18);border-radius:14px;background:linear-gradient(135deg,rgba(240,253,244,.90),rgba(239,246,255,.76));padding:8px 10px;margin:.18rem 0 .35rem 0;}
        .ai-lite-recognition-card b{color:#0f172a;font-weight:950}.ai-lite-recognition-card span{font-weight:900;color:#0369a1;}
        div[data-testid="stButton"] button{min-height:31px!important;border-radius:999px!important;font-weight:800!important;padding:.14rem .44rem!important;font-size:.78rem!important;}
        textarea, input{font-size:15px!important;}
        .ai-lite-shadow-suggestions{border:1px solid rgba(14,165,233,.16);border-radius:14px;background:linear-gradient(135deg,rgba(248,250,252,.90),rgba(239,246,255,.76));padding:7px 9px;margin:.15rem 0 .35rem 0;box-shadow:0 7px 18px rgba(15,23,42,.045);}
        .ai-lite-shadow-title{font-size:.73rem;font-weight:950;color:#0369a1;margin-bottom:3px;}
        .ai-lite-shadow-row{font-size:.74rem;color:#334155;margin:2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
        .ai-lite-compact-note{font-size:.72rem;color:#64748b;line-height:1.25;}
        section[data-testid="stSidebar"]{max-width:285px;}
        @media(max-width:780px){
          .ai-lite-shell{padding:10px;border-radius:16px;margin:.22rem 0 .42rem 0;}
          .ai-lite-title{font-size:.98rem}.ai-lite-context{font-size:.80rem}.ai-lite-warning{font-size:.74rem;padding:7px 9px;}
          .ai-lite-qbox{padding:8px 9px;border-radius:14px}.ai-lite-qbox-title{font-size:.88rem}.ai-lite-qbox-note{font-size:.72rem;}
          div[data-testid="stMetric"]{padding:.15rem 0!important;}
          div[data-testid="stButton"] button{min-height:44px;font-size:.86rem;padding:.28rem .55rem;}
          .stChatMessage{padding:.25rem .35rem!important;margin:.15rem 0!important;}
          [data-testid="stVerticalBlock"]{gap:.35rem!important;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Sidebar stability: no DOM close script here. Native Streamlit + main-page menu handle open/close.


def _filter_prepared_questions(category: str, search: str, limit: int = 80) -> List[Dict[str, Any]]:
    category = category or "All Questions"
    cleaned_search = _plain_normalize_question_pattern(search or "")
    alias_map = {
        "en": "entry", "ent": "entry", "enter": "entry",
        "tp": "take profit target", "sl": "stop loss risk",
        "reg": "regime", "pred": "prediction", "hist": "history similar",
        "risk": "risk exit protect", "qual": "quality confidence reliability",
    }
    if cleaned_search in alias_map:
        cleaned_search = alias_map[cleaned_search]
    terms = [t for t in cleaned_search.split() if t]
    rows: List[Tuple[float, Dict[str, Any]]] = []
    for item in PREPARED_QUESTION_PATTERNS:
        if category != "All Questions" and item.get("category") != category:
            continue
        pattern = _safe_str(item.get("pattern"), "")
        keywords = " ".join(map(str, item.get("keywords", []))).lower()
        if not cleaned_search:
            score = 1.0
        else:
            score = _similar(cleaned_search, pattern)
            score += sum(0.25 for t in terms if t in pattern or t in keywords)
            if cleaned_search in pattern:
                score += 0.8
        if score > 0.18 or not cleaned_search:
            rows.append((score, item))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in rows[:limit]]


def _smart_question_suggestions(ctx: Dict[str, Any]) -> List[str]:
    c = ctx.get("current", {})
    suggestions: List[str] = []
    exit_risk = _metric(c, "exit_risk", 5)
    entry = _metric(c, "entry_score", 5)
    buy = _num(c.get("buy_pressure"))
    sell = _num(c.get("sell_pressure"))
    conf = _metric(c, "forecast_confidence", 50)
    tp = _metric(c, "tp_score", 5)
    regime_side = _direction_from_regime(c.get("regime"))
    pred_side = _safe_str(c.get("prediction_direction"), "-").upper()
    has_history = any(_is_df(ctx.get(k, pd.DataFrame())) for k in ["history_df", "regime_history_df", "overlap_history_df", "prediction_history_df"])

    def add(q: str) -> None:
        if q not in suggestions and len(suggestions) < 3:
            suggestions.append(q)

    if exit_risk >= 6.5:
        add("Should I protect my position now?")
    if entry >= 6.5 and exit_risk < 6.5:
        add("Is scalp entry allowed now?")
    if buy is not None and sell is not None and buy > sell:
        add("Is BUY safer now?")
    if buy is not None and sell is not None and sell > buy:
        add("Is SELL safer now?")
    if conf < 50:
        add("Should I wait instead of entering?")
    if tp >= 6.2:
        add("What TP zone is safer?")
    if regime_side in {"BUY", "SELL"} and pred_side in {"BUY", "SELL"} and regime_side != pred_side:
        add("Is regime conflicting with prediction?")
    if has_history:
        add("Find similar setup from history")
    for fallback in ["BUY or SELL safer?", "What next 30 min price prediction?", "Quick trade summary"]:
        add(fallback)
    return suggestions[:3]


def _render_question_box(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """One compact dropdown + one button for all prepared questions.

    The old UI showed category boxes, search boxes, smart-pickers, recent pickers,
    and several buttons.  This keeps the 200+ question library but hides it in
    one expander so the AI tab stays calm on iPhone 11 Pro.
    """
    state_key = f"ai_lite_question_box_value_{UNIQUE}"
    if state_key not in st.session_state:
        st.session_state[state_key] = ""

    prompt_to_submit: Optional[str] = None
    selected_category = "All Questions"
    selected_label = ""
    answer_mode = "Auto"

    labels: List[str] = []
    label_to_item: Dict[str, Dict[str, Any]] = {}
    for item in PREPARED_QUESTION_PATTERNS:
        q = _safe_str(item.get("question"), "")
        cat = _safe_str(item.get("category"), "All Questions")
        if not q:
            continue
        label = f"{cat} — {q}"
        # Keep labels unique without adding another UI box.
        if label in label_to_item:
            label = f"{label} #{len(label_to_item) + 1}"
        labels.append(label)
        label_to_item[label] = item

    if not labels:
        labels = ["Bias / Direction — BUY or SELL safer?"]
        label_to_item[labels[0]] = {"question": "BUY or SELL safer?", "category": "Bias / Direction"}

    with st.expander(f"📦 Question Box — {len(PREPARED_QUESTION_PATTERNS)} prepared questions", expanded=False):
        st.markdown(
            "<div class='ai-lite-qbox-note'>One dropdown only. Choose any prepared question, then press one button. For your own words, use the Smart Text Input above; bad grammar and typos are supported.</div>",
            unsafe_allow_html=True,
        )
        selected_label = st.selectbox(
            "All prepared questions",
            labels,
            key=f"question_onebox_select_{UNIQUE}",
            help="All local question patterns are here. No wall of buttons. The selected question still goes through the same local NLP pipeline.",
        )
        selected_item = label_to_item.get(selected_label, {})
        selected_question = _safe_str(selected_item.get("question"), selected_label.split("—", 1)[-1].strip())
        selected_category = _safe_str(selected_item.get("category"), "All Questions")
        if st.button("Ask Selected Question", use_container_width=True, key=f"ask_onebox_{UNIQUE}"):
            prompt_to_submit = selected_question
            st.session_state[state_key] = selected_question

    return {
        "prompt": prompt_to_submit,
        "category": selected_category,
        "answer_mode": answer_mode,
        "search": "one_dropdown_all_patterns",
        "selected_question": selected_label,
        "total_patterns": len(PREPARED_QUESTION_PATTERNS),
    }



def _render_text_recognition_card(parsed: Dict[str, Any], ctx: Dict[str, Any]) -> None:
    try:
        c = ctx.get("current", {})
        intent = _safe_str(parsed.get("intent_label"), "nearest useful answer")
        norm = _safe_str(parsed.get("normalized_question"), "-")
        sim = _safe_str(parsed.get("similarity_score"), "0")
        strength = _safe_str(parsed.get("match_strength"), "weak").upper()
        side = _safe_str(parsed.get("direction_keyword") or _safer_bias(c)[0], "WAIT")
        st.markdown(
            f"""
            <div class="ai-lite-recognition-card">
              <b>Recognition result:</b> {intent} • Match <b>{sim}%</b> / {strength} • Side <b>{side}</b><br/>
              <span>Normalized:</span> {norm}
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def _render_smart_text_input_box(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """One compact combined input box with shadow KNN/Greedy suggestions."""
    state_key = f"ai_lite_smart_text_{UNIQUE}"
    clear_key = f"{state_key}_clear_next"
    if st.session_state.get(clear_key):
        st.session_state[state_key] = ""
        st.session_state[clear_key] = False
    st.session_state.setdefault(state_key, "")
    st.markdown(
        """
        <div class="ai-lite-smart-input-head">
          <b>🧠 One Combined Chat Input</b><br/>
          <span>Type en / entry / tp / regime / risk / prediction. Shadow suggestions appear below; all use the same local NLP pipeline.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    raw_text = st.text_area(
        "Ask AI Assistant Lite",
        height=58,
        key=state_key,
        placeholder="Type here only one input: en, entry now, tp for sell entry, regime conflict, prediction path, risk now...",
        label_visibility="collapsed",
        help="Local only. No OpenAI API. Uses existing Home/Lunch/Data Visualization metrics and history.",
    )
    search_text = str(raw_text or "en").strip() or "en"
    related = _filter_prepared_questions("All Questions", search_text, limit=8)
    st.markdown('<div class="ai-lite-shadow-suggestions"><div class="ai-lite-shadow-title">Shadow related questions — KNN/Greedy priority ascending</div>', unsafe_allow_html=True)
    for idx, item in enumerate(related[:6], 1):
        st.markdown(f"<div class='ai-lite-shadow-row'>#{idx} • {_safe_str(item.get('category'))} — {_safe_str(item.get('question'))}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    prompt_to_submit: Optional[str] = None
    preview = None
    use_top = False

    def _submit_current_text() -> str:
        if use_top and related:
            return _safe_str(related[0].get("question"), str(raw_text or ""))
        return str(raw_text or "").strip()

    c0, c1, c2, c3 = st.columns([1.05, 1.0, 1.0, .72])
    with c0:
        use_top = st.checkbox("Use top matched question", value=False, key=f"use_top_match_{UNIQUE}", help="Checkbox near input. If enabled, Analyze / Answer uses the #1 shadow question; otherwise it uses your typed text.")
    with c1:
        if st.button("🚀 Analyze", use_container_width=True, key=f"smart_text_ask_{UNIQUE}"):
            prompt_to_submit = _submit_current_text()
            try:
                from core.styles import request_close_sidebar
                request_close_sidebar()
            except Exception:
                pass
    with c2:
        if st.button("✅ Answer", use_container_width=True, key=f"smart_text_answer_now_{UNIQUE}", help="Answer the question typed in the input field using the same local NLP analysis."):
            prompt_to_submit = _submit_current_text()
            try:
                from core.styles import request_close_sidebar
                request_close_sidebar()
            except Exception:
                pass
    with c3:
        if st.button("⌫ Reset", use_container_width=True, key=f"smart_text_reset_{UNIQUE}"):
            st.session_state[clear_key] = True
            try:
                from core.styles import request_close_sidebar
                request_close_sidebar()
            except Exception:
                pass
            st.rerun()
    if str(raw_text or "").strip():
        preview = local_ai_detect_intent(str(raw_text))
        with st.expander("Open / Close — Local NLP recognition", expanded=False):
            _render_text_recognition_card(preview, ctx)
            st.caption("This replaces the old always-open local NLP/past field to reduce screen clutter and iPhone RAM/UI load.")
    return {"prompt": prompt_to_submit, "preview": preview, "category": "Smart Text", "answer_mode": "Auto"}

def _answer_section(answer: str, label: str) -> str:
    try:
        pat = r"\*\*" + re.escape(label) + r":\*\*\s*(.*?)(?=\n\n\*\*|\n\nRecommendation card|\n\n_System decision|\Z)"
        m = re.search(pat, answer, flags=re.S)
        return m.group(1).strip() if m else "-"
    except Exception:
        return "-"


def _apply_answer_mode(answer: str, answer_mode: str, parsed: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    mode = answer_mode or "Auto"
    intent = _safe_str(parsed.get("intent"), "")
    if mode == "Auto":
        if "tp" in intent:
            mode = "TP Plan"
        elif "history" in intent:
            mode = "History Mining"
        elif "scalp" in intent or "entry" in intent:
            mode = "Fast Scalp"
        else:
            return answer
    if mode == "Full Explain":
        return answer

    interpreted = _answer_section(answer, "Interpreted question")
    direct = _answer_section(answer, "Direct answer")
    safer = _answer_section(answer, "Safer bias")
    tp = _answer_section(answer, "TP / price zone")
    mining = _answer_section(answer, "Data mining insight")
    risk = _answer_section(answer, "Main risk")
    conf = _answer_section(answer, "Confidence")

    if mode == "Fast Scalp":
        return (
            f"**Interpreted question:** {interpreted}\n\n"
            f"**Direct answer:** {direct}\n\n"
            f"**Safer bias:** {safer}\n\n"
            f"**TP / price zone:** {tp}\n\n"
            f"**Main risk:** {risk}\n\n"
            f"**Confidence:** {conf}\n\n"
            "_System decision still controls._"
        )
    if mode == "TP Plan":
        return (
            f"**Interpreted question:** {interpreted}\n\n"
            f"**TP / price zone:** {tp}\n\n"
            f"**Direct answer:** {direct}\n\n"
            f"**Main risk:** {risk}\n\n"
            f"**Confidence:** {conf}\n\n"
            "_For exact TP, tell me your entry price if it was not detected._"
        )
    if mode == "History Mining":
        return (
            f"**Interpreted question:** {interpreted}\n\n"
            f"**Data mining insight:** {mining}\n\n"
            f"**Direct answer:** {direct}\n\n"
            f"**Safer bias:** {safer}\n\n"
            f"**Confidence:** {conf}\n\n"
            "_History/data mining uses existing rows only; system decision still controls._"
        )
    return answer


def _latest_ai_result_text() -> str:
    try:
        for msg in reversed(st.session_state.get("ai_lite_messages", [])):
            if _safe_str(msg.get("role"), "").lower() == "assistant":
                content = _safe_str(msg.get("content"), "")
                if content:
                    return content
    except Exception:
        pass
    return "No AI answer yet. Type your question below, then click **Analyze** or **Answer**."


def render_ai_assistant_lite_tab() -> None:
    _inject_mobile_css()
    try:
        from core.styles import request_close_sidebar
        request_close_sidebar()
    except Exception:
        pass

    ctx = build_ai_context_from_existing_data()
    c = ctx.get("current", {})

    st.markdown(
        f"""
        <div class="ai-lite-shell">
          <div class="ai-lite-header">
            <div class="ai-lite-title">🤖 AI Assistant Lite — inside Research</div>
            <div class="ai-lite-badge">No API • EURUSD H1</div>
          </div>
          <div class="ai-lite-context">
            <b>Market context:</b> {_safe_str(c.get('symbol'),'EURUSD')} {_safe_str(c.get('timeframe'),'H1')} •
            Decision <b>{_safe_str(c.get('decision'))}</b> • Direction <b>{_safe_str(c.get('direction'))}</b> •
            Regime <b>{_safe_str(c.get('regime'))}</b><br/>
            Entry {_fmt_score(c.get('entry_score'))} • TP {_fmt_score(c.get('tp_score'))} • Exit Risk {_fmt_score(c.get('exit_risk'))} •
            Buy {_fmt_score(c.get('buy_pressure'))} / Sell {_fmt_score(c.get('sell_pressure'))} • Forecast {_fmt_score(c.get('forecast_confidence'))}%
          </div>
        </div>
        <div class="ai-lite-warning">Result display is placed first. The choice box and input field are below. Local assistant only; it reads existing metrics and must not override system decision.</div>
        """,
        unsafe_allow_html=True,
    )

    if "ai_lite_messages" not in st.session_state:
        st.session_state["ai_lite_messages"] = [{
            "role": "assistant",
            "content": "Ask with bad spelling too: ‘whta bias less risky hold nxt 1h’, ‘tp for seel entry’, or ‘what nxt 30m price’. I will use nearest useful local answer.",
            "meta": {},
        }]
    if "ai_lite_question_memory" not in st.session_state:
        st.session_state["ai_lite_question_memory"] = []
    if "ai_lite_answer_memory" not in st.session_state:
        st.session_state["ai_lite_answer_memory"] = []

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Data", "READY" if ctx.get("data_available") else "Need Run")
    m2.metric("Safer Bias", _safer_bias(c)[0])
    m3.metric("Risk", _risk_level(c))
    m4.metric("Missing", str(len(ctx.get("missing_fields", []))))

    # Result first, before the question box and input field.
    st.markdown("### ✅ AI Result Display")
    result_text = _latest_ai_result_text()
    with st.container():
        st.markdown(result_text)

    last_payload = st.session_state.get("ai_lite_last_copy_payload", "No AI answer yet.")
    copy_cols = st.columns([1, 1, .72])
    with copy_cols[0]:
        _copy_button("📋 Copy Last AI Answer", last_payload, f"copy_last_ai_{UNIQUE}")
    with copy_cols[1]:
        _copy_button("📋 Copy Full AI Chat", _full_chat_copy(ctx), f"copy_full_ai_{UNIQUE}")
    with copy_cols[2]:
        if st.button("🧹 Clear", use_container_width=True, key=f"clear_{UNIQUE}"):
            st.session_state["ai_lite_messages"] = []
            st.session_state["ai_lite_last_copy_payload"] = "No AI answer yet."
            st.rerun()

    with st.expander("Open / Close — Full AI chat history", expanded=False):
        for msg in st.session_state.get("ai_lite_messages", [])[-16:]:
            with st.chat_message(msg.get("role", "assistant")):
                st.markdown(msg.get("content", ""))

    last_recognition = st.session_state.get("ai_lite_last_recognition", {})
    if isinstance(last_recognition, dict) and last_recognition.get("normalized_question"):
        with st.expander("Open / Close — Last local NLP recognition", expanded=False):
            _render_text_recognition_card(last_recognition, ctx)
            st.caption("Recognition is hidden by default so the AI page stays clean on mobile.")

    st.markdown("### ✍️ Ask / Choose Question")
    smart_box = _render_smart_text_input_box(ctx)
    qbox = _render_question_box(ctx)
    selected_prompt = smart_box.get("prompt") or qbox.get("prompt")
    selected_category = _safe_str(smart_box.get("category") if smart_box.get("prompt") else qbox.get("category"), "-")
    answer_mode = _safe_str(smart_box.get("answer_mode") if smart_box.get("prompt") else qbox.get("answer_mode"), "Auto")

    # 2026-06-14: keep only one input box. The old bottom st.chat_input is removed to avoid duplicate chat fields.
    prompt = selected_prompt
    if prompt:
        parsed = local_ai_detect_intent(prompt)
        parsed["selected_question_category"] = selected_category if selected_prompt else "Free Chat"
        parsed["answer_mode"] = answer_mode
        answer = local_ai_generate_answer(parsed, ctx)
        answer = _apply_answer_mode(answer, answer_mode, parsed, ctx)
        st.session_state["ai_lite_messages"].append({
            "role": "user",
            "content": prompt,
            "meta": {
                "normalized_question": parsed.get("normalized_question", ""),
                "selected_question_category": parsed.get("selected_question_category", "-"),
                "answer_mode": answer_mode,
            },
        })
        st.session_state["ai_lite_messages"].append({"role": "assistant", "content": answer, "meta": parsed})
        st.session_state["ai_lite_messages"] = st.session_state["ai_lite_messages"][-32:]
        _store_question_memory(prompt, parsed.get("normalized_question", ""), parsed.get("intent", "nearest_answer_fallback"), answer)
        payload = _copy_payload(prompt, parsed, answer, ctx, parsed.get("selected_question_category", "-"), answer_mode)
        st.session_state["ai_lite_last_copy_payload"] = payload
        st.session_state["ai_lite_last_context"] = _json_safe({
            "selected_question_category": parsed.get("selected_question_category"),
            "answer_mode": answer_mode,
            "raw_question": prompt,
            "normalized_question": parsed.get("normalized_question"),
            "intent": parsed.get("intent"),
            "similarity_score": parsed.get("similarity_score"),
            "context_snapshot": _context_snapshot_text(ctx),
            "missing_fields": ctx.get("missing_fields", []),
            "prepared_question_patterns": len(PREPARED_QUESTION_PATTERNS),
        })
        st.session_state["ai_lite_last_recognition"] = {
            "intent_label": parsed.get("intent_label"),
            "normalized_question": parsed.get("normalized_question"),
            "similarity_score": parsed.get("similarity_score"),
            "match_strength": parsed.get("match_strength"),
            "direction_keyword": parsed.get("direction_keyword"),
        }
        try:
            from core.styles import request_close_sidebar
            request_close_sidebar()
        except Exception:
            pass
        st.rerun()

# =====================================================================
# 2026-06-14 FINAL AI ASSISTANT INTELLIGENCE CENTER OVERRIDE
# Clean UI: one input box, one selector, one Analyze button, one result box.
# Uses existing local NLP, fuzzy matching, prepared question patterns, history,
# regime/priority/reliability context only. No API and no heavy model.
# =====================================================================

def render_ai_assistant_intelligence_center_20260614() -> None:
    _inject_mobile_css()
    try:
        from core.styles import request_close_sidebar
        request_close_sidebar()
    except Exception:
        pass
    ctx = build_ai_context_from_existing_data()
    if "ai_lite_messages" not in st.session_state:
        st.session_state["ai_lite_messages"] = []
    if "ai_lite_question_memory" not in st.session_state:
        st.session_state["ai_lite_question_memory"] = []
    if "ai_lite_answer_memory" not in st.session_state:
        st.session_state["ai_lite_answer_memory"] = []

    st.markdown("### 🤖 AI Assistant Intelligence Center")
    st.caption("One input, one selector, one Analyze button, one result box. Local only: NLP keyword matching, fuzzy matching, TF-IDF-style similarity when available, history/regime/priority/reliability-aware answer.")

    labels = ["Use typed question"]
    label_to_item = {"Use typed question": {"question": "", "category": "Free Chat"}}
    for item in PREPARED_QUESTION_PATTERNS:
        q = _safe_str(item.get("question"), "")
        cat = _safe_str(item.get("category"), "All Questions")
        if not q:
            continue
        label = f"{cat} — {q}"
        if label in label_to_item:
            label = f"{label} #{len(label_to_item)}"
        labels.append(label)
        label_to_item[label] = item

    selected_label = st.selectbox(
        "One question selector",
        labels,
        key=f"ai_intelligence_one_selector_{UNIQUE}",
        help="All prepared local question patterns are inside this one selector.",
    )
    raw_text = st.text_area(
        "One question input box",
        height=74,
        key=f"ai_intelligence_one_input_{UNIQUE}",
        placeholder="Type one question: entry now, tp for sell entry, regime conflict, risk now, best hour, prediction error...",
        help="Bad spelling is accepted. The local NLP normalizer and fuzzy matcher will clean it.",
    )
    if st.button("🚀 Analyze", key=f"ai_intelligence_one_analyze_{UNIQUE}", use_container_width=True):
        selected_item = label_to_item.get(selected_label, {})
        prompt = str(raw_text or "").strip() or _safe_str(selected_item.get("question"), "BUY or SELL safer?")
        category = _safe_str(selected_item.get("category"), "Free Chat") if not raw_text.strip() else "Free Chat"
        parsed = local_ai_detect_intent(prompt)
        parsed["selected_question_category"] = category
        parsed["answer_mode"] = "Auto"
        answer = local_ai_generate_answer(parsed, ctx)
        answer = _apply_answer_mode(answer, "Auto", parsed, ctx)
        # Reliability/regime/priority warning summary from existing context.
        current = ctx.get("current", {}) if isinstance(ctx, dict) else {}
        warning_bits = []
        if _risk_level(current).upper() in {"HIGH", "DANGER", "AVOID"}:
            warning_bits.append("Risk warning active")
        if _safe_str(current.get("regime"), "").upper() and _safe_str(current.get("direction"), "").upper() not in {"", "WAIT", "NEUTRAL"}:
            warning_bits.append(f"Regime-aware answer: {current.get('regime')}")
        if ctx.get("missing_fields"):
            warning_bits.append(f"Missing fields: {len(ctx.get('missing_fields', []))}")
        if warning_bits:
            answer = answer + "\n\nReliability-aware warning: " + " • ".join(warning_bits)
        st.session_state["ai_lite_messages"].append({"role": "user", "content": prompt, "meta": {"category": category}})
        st.session_state["ai_lite_messages"].append({"role": "assistant", "content": answer, "meta": parsed})
        st.session_state["ai_lite_messages"] = st.session_state["ai_lite_messages"][-32:]
        _store_question_memory(prompt, parsed.get("normalized_question", ""), parsed.get("intent", "nearest_answer_fallback"), answer)
        payload = _copy_payload(prompt, parsed, answer, ctx, category, "Auto")
        st.session_state["ai_lite_last_copy_payload"] = payload
        st.session_state["ai_lite_last_answer_summary_20260614"] = payload
        st.session_state["ai_lite_last_recognition"] = {
            "intent_label": parsed.get("intent_label"),
            "normalized_question": parsed.get("normalized_question"),
            "similarity_score": parsed.get("similarity_score"),
            "match_strength": parsed.get("match_strength"),
            "direction_keyword": parsed.get("direction_keyword"),
        }

    result_text = _latest_ai_result_text()
    st.text_area(
        "One result output box",
        value=result_text,
        height=300,
        key=f"ai_intelligence_one_result_{UNIQUE}",
        disabled=True,
    )

# Override the older multi-control renderer with the clean final center.
def render_ai_assistant_lite_tab() -> None:  # type: ignore[no-redef]
    render_ai_assistant_intelligence_center_20260614()
