"""SPIBB, HCOPE and doubly robust off-policy safety diagnostics.

This module evaluates only logged, settled behavior.  Missing behavior
propensities make OPE non-identifiable; probabilities are never reconstructed
from scores, confidence labels, or realized returns.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import json
import math

import numpy as np
import pandas as pd

VERSION = "off-policy-evaluation-20260621-v1"
ACTIONS = ("BUY", "SELL", "WAIT")


def _finite(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _vector(value: Any) -> dict[str, float] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return None
    if not isinstance(value, Mapping):
        return None
    out: dict[str, float] = {}
    for action in ACTIONS:
        raw = value.get(action, value.get(action.lower()))
        x = _finite(raw)
        if x is None or x < 0 or x > 1:
            return None
        out[action] = x
    total = sum(out.values())
    if not 0.999 <= total <= 1.001:
        return None
    return {key: val / total for key, val in out.items()}


def _bucket_value(row: Mapping[str, Any], key: str, fallback: str = "UNKNOWN") -> str:
    value = row.get(key)
    if value in (None, ""):
        return fallback
    if key in {"forecast_agreement", "spread"}:
        x = _finite(value)
        if x is None:
            return fallback
        if key == "forecast_agreement":
            if x > 1:
                x /= 100.0
            return "LOW" if x < 0.45 else ("MEDIUM" if x < 0.70 else "HIGH")
        if x < 0.01:
            return "LOW" if x <= 0.00008 else ("MEDIUM" if x <= 0.00016 else "HIGH")
        return "LOW" if x <= 0.8 else ("MEDIUM" if x <= 1.6 else "HIGH")
    return str(value).upper().strip() or fallback


def support_bucket(row: Mapping[str, Any]) -> str:
    fields = (
        _bucket_value(row, "h1_regime", _bucket_value(row, "major_regime")),
        _bucket_value(row, "session"),
        _bucket_value(row, "volatility_bucket"),
        _bucket_value(row, "spread_bucket", _bucket_value(row, "spread")),
        _bucket_value(row, "forecast_agreement"),
        _bucket_value(row, "conflict_status"),
        _bucket_value(row, "counter_trend_status"),
        _bucket_value(row, "candidate_action", _bucket_value(row, "baseline_action", "WAIT")),
    )
    return "|".join(fields)


def derive_spibb_support_threshold(
    *,
    confidence_target: float,
    max_policy_deviation: float,
    observed_bucket_count: int,
    action_count: int = 3,
) -> dict[str, Any]:
    """Union-bound support threshold used by the baseline-bootstrap gate.

    N_min = ceil(2 / epsilon^2 * log(2 * B * A / delta)), where
    delta=1-confidence_target, B is the number of point-in-time support buckets,
    and A is the action count.  This is a documented conservative concentration
    threshold, not a claim that the full SPIBB MDP theorem applies to trading.
    """
    confidence = min(0.999, max(0.50, float(confidence_target)))
    epsilon = min(1.0, max(0.05, float(max_policy_deviation)))
    delta = max(1e-9, 1.0 - confidence)
    buckets = max(1, int(observed_bucket_count))
    actions = max(1, int(action_count))
    threshold = int(math.ceil((2.0 / (epsilon * epsilon)) * math.log((2.0 * buckets * actions) / delta)))
    return {
        "threshold": threshold,
        "confidence_target": confidence,
        "delta": delta,
        "max_policy_deviation": epsilon,
        "observed_bucket_count": buckets,
        "action_count": actions,
        "formula": "ceil((2/epsilon^2)*log((2*bucket_count*action_count)/delta))",
        "theorem_boundary": "Conservative support rule; no finite-MDP trading guarantee is claimed.",
    }


def evaluate_spibb_support(
    settled: pd.DataFrame,
    *,
    confidence_target: float = 0.95,
    max_policy_deviation: float = 0.25,
) -> dict[str, Any]:
    if not isinstance(settled, pd.DataFrame) or settled.empty:
        threshold = derive_spibb_support_threshold(
            confidence_target=confidence_target,
            max_policy_deviation=max_policy_deviation,
            observed_bucket_count=1,
        )
        return {
            "status": "INSUFFICIENT_EVIDENCE", "support_coverage": 0.0,
            "supported_bucket_count": 0, "total_bucket_count": 0,
            "baseline_bootstrap_required": True, "threshold_diagnostic": threshold,
            "bucket_counts": {},
        }
    data = settled.copy(deep=False)
    data = data.loc[data.get("record_status", pd.Series("", index=data.index)).astype(str).str.upper().eq("SETTLED")]
    if data.empty:
        return evaluate_spibb_support(pd.DataFrame(), confidence_target=confidence_target, max_policy_deviation=max_policy_deviation)
    data = data.assign(__bucket=[support_bucket(row) for row in data.to_dict("records")])
    counts = data["__bucket"].value_counts().sort_index()
    diagnostic = derive_spibb_support_threshold(
        confidence_target=confidence_target,
        max_policy_deviation=max_policy_deviation,
        observed_bucket_count=len(counts),
    )
    threshold = int(diagnostic["threshold"])
    supported = counts[counts >= threshold]
    coverage = float(data["__bucket"].isin(supported.index).mean()) if len(data) else 0.0
    return {
        "status": "SUPPORTED" if len(supported) and coverage >= 0.80 else "BASELINE_BOOTSTRAP",
        "support_coverage": coverage,
        "supported_bucket_count": int(len(supported)),
        "total_bucket_count": int(len(counts)),
        "baseline_bootstrap_required": not (len(supported) and coverage >= 0.80),
        "threshold_diagnostic": diagnostic,
        "bucket_counts": {str(k): int(v) for k, v in counts.items()},
    }


def _valid_ope_rows(settled: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    reasons: list[str] = []
    if not isinstance(settled, pd.DataFrame) or settled.empty:
        return pd.DataFrame(), ["NO_SETTLED_POLICY_LEDGER"]
    data = settled.copy(deep=False)
    status = data.get("record_status", pd.Series("", index=data.index)).astype(str).str.upper()
    data = data.loc[status.eq("SETTLED")].copy()
    if data.empty:
        return data, ["NO_COST_COMPLETE_SETTLED_OUTCOMES"]
    for column in ("behavior_action_probability", "candidate_probability_of_behavior_action", "net_return_fraction"):
        data[column] = pd.to_numeric(data.get(column), errors="coerce")
    missing = data[["behavior_action_probability", "candidate_probability_of_behavior_action", "net_return_fraction"]].isna().any(axis=1)
    if missing.any():
        reasons.append("MISSING_LOGGED_PROPENSITY_OR_NET_RETURN")
    data = data.loc[~missing]
    invalid = (
        data["behavior_action_probability"].le(0)
        | data["behavior_action_probability"].gt(1)
        | data["candidate_probability_of_behavior_action"].lt(0)
        | data["candidate_probability_of_behavior_action"].gt(1)
    )
    if invalid.any():
        reasons.append("INVALID_PROPENSITY_RANGE")
    data = data.loc[~invalid]
    return data, reasons


def _bounded_hoeffding_lower(
    values: np.ndarray,
    *,
    confidence: float,
    lower_bound: float,
    upper_bound: float,
    effective_sample_size: float,
) -> float | None:
    """Distribution-free one-sided LCB for a predeclared bounded range.

    The guarantee requires independent bounded samples. For EURUSD H1 the
    reported value is therefore a conservative diagnostic; serial dependence is
    additionally guarded by chronological evidence and effective-support gates.
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    n_eff = float(effective_sample_size)
    if len(values) < 2 or n_eff < 2:
        return None
    delta = max(1e-12, 1.0 - min(0.999, max(0.50, float(confidence))))
    width = max(1e-12, float(upper_bound) - float(lower_bound))
    radius = width * math.sqrt(math.log(1.0 / delta) / (2.0 * n_eff))
    return float(values.mean() - radius)


def evaluate_hcope(
    settled: pd.DataFrame,
    *,
    confidence_target: float = 0.95,
    weight_clip: float = 20.0,
    min_effective_sample_size: float = 30.0,
    max_weight_share: float = 0.20,
    reward_bound: float = 0.10,
) -> dict[str, Any]:
    data, reasons = _valid_ope_rows(settled)
    raw_n = int(len(settled)) if isinstance(settled, pd.DataFrame) else 0
    if data.empty:
        return {
            "status": "NOT_IDENTIFIABLE", "ope_status": "NOT_IDENTIFIABLE",
            "policy_promotion_allowed": False, "raw_sample_count": raw_n,
            "identifiable_sample_count": 0, "effective_sample_size": 0.0,
            "support_coverage": 0.0, "maximum_importance_weight": None,
            "weight_concentration": None, "clipped_estimate": None,
            "unclipped_estimate": None, "lower_confidence_bound": None,
            "failure_reason": reasons or ["PROPENSITY_ABSENT"],
        }
    behavior = data["behavior_action_probability"].to_numpy(float)
    candidate = data["candidate_probability_of_behavior_action"].to_numpy(float)
    reward = data["net_return_fraction"].to_numpy(float)
    weights = candidate / behavior
    clipped = np.minimum(weights, float(weight_clip))
    effective_n = float(weights.sum() ** 2 / max(np.square(weights).sum(), 1e-12))
    max_weight = float(weights.max())
    concentration = float(weights.max() / max(weights.sum(), 1e-12))
    is_values = weights * reward
    bounded_reward = np.clip(reward, -abs(float(reward_bound)), abs(float(reward_bound)))
    clipped_values = clipped * bounded_reward
    unclipped_estimate = float(is_values.mean())
    clipped_estimate = float(clipped_values.mean())
    lower = _bounded_hoeffding_lower(
        clipped_values, confidence=confidence_target,
        lower_bound=-abs(float(weight_clip) * float(reward_bound)),
        upper_bound=abs(float(weight_clip) * float(reward_bound)),
        effective_sample_size=effective_n,
    )
    coverage = float(len(data) / max(raw_n, 1))
    failures = list(reasons)
    if effective_n < min_effective_sample_size:
        failures.append("LOW_EFFECTIVE_SAMPLE_SIZE")
    if concentration > max_weight_share:
        failures.append("EXTREME_WEIGHT_CONCENTRATION")
    if max_weight > weight_clip * 2:
        failures.append("EXTREME_UNCLIPPED_WEIGHT")
    if coverage < 0.80:
        failures.append("INSUFFICIENT_PROPENSITY_COVERAGE")
    status = "EVALUATED" if not failures and lower is not None else "BLOCKED"
    return {
        "status": status, "ope_status": status,
        "policy_promotion_allowed": status == "EVALUATED",
        "raw_sample_count": raw_n, "identifiable_sample_count": int(len(data)),
        "effective_sample_size": effective_n, "support_coverage": coverage,
        "maximum_importance_weight": max_weight, "weight_concentration": concentration,
        "clipped_estimate": clipped_estimate, "unclipped_estimate": unclipped_estimate,
        "lower_confidence_bound": lower, "weight_clip": float(weight_clip),
        "reward_bound": abs(float(reward_bound)),
        "lower_bound_method": "One-sided Hoeffding LCB on prebounded clipped importance-weighted returns",
        "dependence_limitation": "Formal coverage requires bounded independent samples; serial dependence is not claimed away.",
        "failure_reason": failures,
    }


def _chronological_q_model(data: pd.DataFrame, train_fraction: float = 0.60) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str], float], dict[str, float]]:
    work = data.copy(deep=False)
    work["__time"] = pd.to_datetime(work.get("decision_timestamp_utc"), errors="coerce", utc=True)
    work = work.loc[work["__time"].notna()].sort_values("__time", kind="mergesort")
    split = max(1, min(len(work) - 1, int(math.floor(len(work) * train_fraction))))
    train = work.iloc[:split].copy()
    test = work.iloc[split:].copy()
    train["__bucket"] = [support_bucket(row) for row in train.to_dict("records")]
    bucket_action = train.groupby(["__bucket", "baseline_action"], dropna=False)["net_return_fraction"].mean().to_dict()
    action_mean = train.groupby("baseline_action", dropna=False)["net_return_fraction"].mean().to_dict()
    return train, test, {(str(k[0]), str(k[1]).upper()): float(v) for k, v in bucket_action.items()}, {str(k).upper(): float(v) for k, v in action_mean.items()}


def evaluate_doubly_robust(
    settled: pd.DataFrame,
    *,
    weight_clip: float = 20.0,
    min_test_rows: int = 20,
) -> dict[str, Any]:
    data, reasons = _valid_ope_rows(settled)
    if len(data) < max(4, min_test_rows):
        return {
            "status": "NOT_IDENTIFIABLE", "doubly_robust_value": None,
            "direct_method_value": None, "importance_sampling_value": None,
            "estimator_disagreement": None, "sample_count": int(len(data)),
            "failure_reason": reasons + ["INSUFFICIENT_CHRONOLOGICAL_ROWS"],
        }
    vectors = data.get("candidate_probability_vector", pd.Series(index=data.index, dtype=object)).map(_vector)
    valid_vectors = vectors.notna()
    if not valid_vectors.all():
        reasons.append("MISSING_FULL_CANDIDATE_PROBABILITY_VECTOR")
    data = data.loc[valid_vectors].copy()
    data["__candidate_vector"] = vectors.loc[valid_vectors]
    if len(data) < min_test_rows:
        return {
            "status": "NOT_IDENTIFIABLE", "doubly_robust_value": None,
            "direct_method_value": None, "importance_sampling_value": None,
            "estimator_disagreement": None, "sample_count": int(len(data)),
            "failure_reason": reasons + ["INSUFFICIENT_VECTOR_SUPPORT"],
        }
    train, test, bucket_action, action_mean = _chronological_q_model(data)
    if test.empty:
        return {
            "status": "NOT_IDENTIFIABLE", "doubly_robust_value": None,
            "direct_method_value": None, "importance_sampling_value": None,
            "estimator_disagreement": None, "sample_count": 0,
            "failure_reason": reasons + ["EMPTY_CHRONOLOGICAL_TEST_WINDOW"],
        }
    global_mean = float(train["net_return_fraction"].mean())
    dr_values: list[float] = []
    dm_values: list[float] = []
    is_values: list[float] = []
    unsupported = 0
    for row in test.to_dict("records"):
        bucket = support_bucket(row)
        behavior_action = str(row.get("baseline_action") or "WAIT").upper()
        vector = _vector(row.get("candidate_probability_vector"))
        if vector is None:
            unsupported += 1
            continue
        q_by_action = {
            action: bucket_action.get((bucket, action), action_mean.get(action, global_mean))
            for action in ACTIONS
        }
        q_pi = sum(vector[action] * q_by_action[action] for action in ACTIONS)
        q_obs = q_by_action.get(behavior_action, global_mean)
        behavior_prob = _finite(row.get("behavior_action_probability"))
        candidate_behavior_prob = _finite(row.get("candidate_probability_of_behavior_action"))
        reward = _finite(row.get("net_return_fraction"))
        if behavior_prob is None or behavior_prob <= 0 or candidate_behavior_prob is None or reward is None:
            unsupported += 1
            continue
        weight = min(float(weight_clip), candidate_behavior_prob / behavior_prob)
        dr_values.append(q_pi + weight * (reward - q_obs))
        dm_values.append(q_pi)
        is_values.append(weight * reward)
    if len(dr_values) < max(10, min_test_rows // 2):
        reasons.append("INSUFFICIENT_DOUBLY_ROBUST_TEST_SUPPORT")
    dr = float(np.mean(dr_values)) if dr_values else None
    dm = float(np.mean(dm_values)) if dm_values else None
    is_est = float(np.mean(is_values)) if is_values else None
    disagreement = max(abs(dr - dm), abs(dr - is_est), abs(dm - is_est)) if None not in (dr, dm, is_est) else None
    status = "EVALUATED" if dr is not None and not reasons else "BLOCKED"
    return {
        "status": status, "doubly_robust_value": dr, "direct_method_value": dm,
        "importance_sampling_value": is_est, "estimator_disagreement": disagreement,
        "sample_count": int(len(dr_values)), "training_sample_count": int(len(train)),
        "unsupported_test_rows": int(unsupported), "failure_reason": reasons,
        "chronological_split": "Chronological 60% train / 40% test, no outcome-time shuffling",
    }


def evaluate_off_policy_safety(
    settled: pd.DataFrame,
    *,
    confidence_target: float = 0.95,
    max_policy_deviation: float = 0.25,
    weight_clip: float = 20.0,
    reward_bound: float = 0.10,
) -> dict[str, Any]:
    spibb = evaluate_spibb_support(
        settled,
        confidence_target=confidence_target,
        max_policy_deviation=max_policy_deviation,
    )
    hcope = evaluate_hcope(
        settled, confidence_target=confidence_target, weight_clip=weight_clip,
        reward_bound=reward_bound,
    )
    dr = evaluate_doubly_robust(settled, weight_clip=weight_clip)
    disagreement = dr.get("estimator_disagreement")
    failures = list(dict.fromkeys(
        list(hcope.get("failure_reason") or []) + list(dr.get("failure_reason") or [])
        + (["LOW_SPIBB_SUPPORT"] if spibb.get("baseline_bootstrap_required") else [])
    ))
    return {
        "version": VERSION,
        "status": "EVALUATED" if not failures else "BLOCKED",
        "spibb": spibb,
        "hcope": hcope,
        "doubly_robust": dr,
        "estimator_disagreement": disagreement,
        "policy_promotion_allowed": not failures,
        "failure_reason": failures,
    }


__all__ = [
    "VERSION", "support_bucket", "derive_spibb_support_threshold",
    "evaluate_spibb_support", "evaluate_hcope", "evaluate_doubly_robust",
    "evaluate_off_policy_safety",
]
