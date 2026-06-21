"""Bounded explicit-duration validator for the existing canonical regimes.

This reuses regime labels; it is not a second regime classifier.  Durations are
estimated from completed chronological segments with Dirichlet smoothing and
no render-time sampling.
"""
from __future__ import annotations

from typing import Any
import math

import numpy as np
import pandas as pd

VERSION = "hsmm-duration-validator-20260621-v1"


def _regime_column(frame: pd.DataFrame) -> str | None:
    for name in ("major_regime", "h1_regime", "regime", "current_regime", "Regime"):
        if name in frame.columns and frame[name].notna().any():
            return name
    return None


def _time_column(frame: pd.DataFrame) -> str | None:
    for name in ("timestamp", "time", "datetime", "date", "decision_timestamp_utc", "settlement_timestamp"):
        if name in frame.columns:
            return name
    return None


def _segments(regimes: pd.Series) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    current = None
    length = 0
    for raw in regimes.fillna("UNKNOWN").astype(str):
        value = raw.upper().strip() or "UNKNOWN"
        if value == current:
            length += 1
        else:
            if current is not None:
                result.append((current, length))
            current, length = value, 1
    if current is not None:
        result.append((current, length))
    return result


def evaluate_hsmm_duration(
    history: pd.DataFrame,
    *,
    maximum_duration: int = 240,
    smoothing: float = 0.5,
    min_completed_segments: int = 4,
) -> dict[str, Any]:
    if not isinstance(history, pd.DataFrame) or history.empty:
        return {
            "status": "INSUFFICIENT_EVIDENCE", "regime_age": None,
            "regime_duration_distribution": {}, "median_remaining_duration": None,
            "remaining_duration_lower": None, "remaining_duration_upper": None,
            "regime_transition_hazard": None, "duration_surprise": None,
            "overstay_risk": None, "sample_segment_count": 0,
            "calculation_version": VERSION,
        }
    data = history.copy()
    regime_col = _regime_column(data)
    if regime_col is None:
        return evaluate_hsmm_duration(pd.DataFrame())
    time_col = _time_column(data)
    if time_col:
        data["__time"] = pd.to_datetime(data[time_col], errors="coerce", utc=True)
        data = data.loc[data["__time"].notna()].sort_values("__time", kind="mergesort")
    segs = _segments(data[regime_col])
    if not segs:
        return evaluate_hsmm_duration(pd.DataFrame())
    current_regime, age = segs[-1]
    completed = [duration for regime, duration in segs[:-1] if regime == current_regime]
    if not completed:
        return {
            "status": "INSUFFICIENT_EVIDENCE", "canonical_regime": current_regime,
            "regime_age": int(age), "regime_duration_distribution": {},
            "duration_posterior": {}, "median_remaining_duration": None,
            "remaining_duration_lower": None, "remaining_duration_upper": None,
            "regime_transition_hazard": None, "duration_surprise": None,
            "overstay_risk": None, "sample_segment_count": 0,
            "all_regime_segment_count": int(max(0, len(segs) - 1)),
            "reuse_contract": "Existing regime labels remain canonical; this module validates duration only.",
            "calculation_version": VERSION,
        }
    max_d = int(max(12, min(maximum_duration, 1000)))
    support = np.arange(1, max_d + 1, dtype=int)
    counts = np.full(max_d, float(max(0.01, smoothing)))
    for duration in completed:
        counts[min(max_d, max(1, int(duration))) - 1] += 1.0
    probabilities = counts / counts.sum()
    survival_at_age = float(probabilities[support >= age].sum())
    if survival_at_age <= 1e-15:
        conditional_support = np.array([0], dtype=int)
        conditional_probs = np.array([1.0], dtype=float)
        hazard = 1.0
    else:
        eligible = support >= age
        conditional_support = support[eligible] - age
        conditional_probs = probabilities[eligible] / probabilities[eligible].sum()
        p_end_now = float(probabilities[min(age, max_d) - 1]) if age <= max_d else 0.0
        hazard = min(1.0, max(0.0, p_end_now / survival_at_age))
    cdf = np.cumsum(conditional_probs)
    quantile = lambda q: int(conditional_support[min(len(conditional_support) - 1, int(np.searchsorted(cdf, q, side="left")))])
    median_remaining, lower, upper = quantile(0.50), quantile(0.10), quantile(0.90)
    observed_tail = float(probabilities[support >= min(age, max_d)].sum())
    surprise = float(-math.log(max(1e-12, observed_tail)))
    overstay = float(probabilities[support <= min(age, max_d)].sum())
    distribution = {str(int(d)): float(p) for d, p in zip(support, probabilities) if p >= 0.0025}
    adequate = len(completed) >= min_completed_segments
    return {
        "status": "PASS" if adequate and overstay < 0.90 else ("INCONCLUSIVE" if not adequate else "OVERSTAY_RISK"),
        "canonical_regime": current_regime, "regime_age": int(age),
        "regime_duration_distribution": distribution,
        "duration_posterior": distribution,
        "median_remaining_duration": median_remaining,
        "remaining_duration_lower": lower, "remaining_duration_upper": upper,
        "regime_transition_hazard": float(hazard), "duration_surprise": surprise,
        "overstay_risk": overstay, "sample_segment_count": int(len(completed)),
        "all_regime_segment_count": int(max(0, len(segs) - 1)),
        "bounded_maximum_duration": max_d,
        "reuse_contract": "Existing regime labels remain canonical; this module validates duration only.",
        "calculation_version": VERSION,
    }


__all__ = ["VERSION", "evaluate_hsmm_duration"]
