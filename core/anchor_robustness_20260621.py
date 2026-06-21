"""Bounded anchor-regression robustness challenger for EURUSD H1.

The implementation is a validator for shifts spanned by pre-decision anchors.
It does not claim causal discovery and never publishes a trading direction.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import math

import numpy as np
import pandas as pd

VERSION = "anchor-robustness-20260621-v1"
DEFAULT_ANCHORS = (
    "session", "day_of_week", "volatility_bucket", "spread_bucket",
    "h1_regime", "data_source_version", "calculation_version_group",
)
DEFAULT_FEATURES = (
    "master_score", "entry_score", "hold_score", "tp_score",
    "exit_risk_score", "forecast_agreement", "reliability", "priority",
)


def _finite(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _categorical_frame(data: pd.DataFrame, columns: Sequence[str]) -> tuple[pd.DataFrame, list[str]]:
    present = [name for name in columns if name in data.columns and data[name].notna().any()]
    if not present:
        return pd.DataFrame(index=data.index), []
    parts = []
    for name in present:
        s = data[name].fillna("UNKNOWN").astype(str).str.upper().str.strip()
        parts.append(pd.get_dummies(s, prefix=name, dtype=float))
    return pd.concat(parts, axis=1) if parts else pd.DataFrame(index=data.index), present


def _numeric_frame(data: pd.DataFrame, columns: Sequence[str]) -> tuple[pd.DataFrame, list[str]]:
    present = []
    out: dict[str, pd.Series] = {}
    for name in columns:
        if name not in data.columns:
            continue
        s = pd.to_numeric(data[name], errors="coerce")
        if s.notna().sum() < max(8, int(len(data) * 0.25)):
            continue
        s = s.fillna(s.median())
        scale = float(s.std(ddof=0))
        out[name] = (s - float(s.mean())) / (scale if scale > 1e-12 else 1.0)
        present.append(name)
    return pd.DataFrame(out, index=data.index), present


def _ridge_fit(x: np.ndarray, y: np.ndarray, penalty: float = 1e-6) -> np.ndarray:
    if x.ndim != 2 or len(x) == 0:
        return np.empty(0)
    design = np.column_stack([np.ones(len(x)), x])
    regularizer = np.eye(design.shape[1]) * float(max(0.0, penalty))
    regularizer[0, 0] = 0.0
    return np.linalg.pinv(design.T @ design + regularizer) @ design.T @ y


def _predict(x: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ beta


def _anchor_transform(x: np.ndarray, y: np.ndarray, anchors: np.ndarray, gamma: float) -> tuple[np.ndarray, np.ndarray]:
    if anchors.size == 0 or gamma <= 1.0:
        return x, y
    z = np.column_stack([np.ones(len(anchors)), anchors])
    projection = z @ np.linalg.pinv(z.T @ z) @ z.T
    factor = math.sqrt(float(gamma)) - 1.0
    transform = np.eye(len(y)) + factor * projection
    return transform @ x, transform @ y


def evaluate_anchor_robustness(
    settled: pd.DataFrame,
    *,
    anchor_columns: Sequence[str] = DEFAULT_ANCHORS,
    feature_columns: Sequence[str] = DEFAULT_FEATURES,
    target_column: str = "net_return_fraction",
    gamma: float = 4.0,
    min_samples: int = 40,
) -> dict[str, Any]:
    """Evaluate robustness to anchor-spanned shifts with chronological holdout.

    All anchors are required to be logged in the decision ledger before the
    outcome.  Missing anchors are reported and never silently reconstructed.
    """
    if not isinstance(settled, pd.DataFrame) or settled.empty:
        return {
            "status": "INSUFFICIENT_EVIDENCE", "anchor_robustness_score": 0.0,
            "anchor_penalty": None, "worst_case_loss": None,
            "coefficient_stability": None, "leave_anchor_level_out": {},
            "robustness_grade": "UNSUPPORTED", "unsupported_shift_warning": True,
            "available_anchors": [], "missing_anchors": list(anchor_columns),
            "sample_count": 0, "calculation_version": VERSION,
        }
    data = settled.copy()
    status = data.get("record_status", pd.Series("", index=data.index)).astype(str).str.upper()
    data = data.loc[status.eq("SETTLED")].copy()
    data[target_column] = pd.to_numeric(data.get(target_column), errors="coerce")
    data = data.loc[data[target_column].notna()].copy()
    if "decision_timestamp_utc" in data.columns:
        data = data.sort_values("decision_timestamp_utc", kind="mergesort")
    anchors, available_anchors = _categorical_frame(data, anchor_columns)
    features, available_features = _numeric_frame(data, feature_columns)
    missing_anchors = [name for name in anchor_columns if name not in available_anchors]
    if len(data) < min_samples or anchors.empty or features.empty:
        return {
            "status": "INSUFFICIENT_EVIDENCE", "anchor_robustness_score": 0.0,
            "anchor_penalty": None, "worst_case_loss": None,
            "coefficient_stability": None, "leave_anchor_level_out": {},
            "robustness_grade": "UNSUPPORTED", "unsupported_shift_warning": True,
            "available_anchors": available_anchors, "missing_anchors": missing_anchors,
            "available_features": available_features, "sample_count": int(len(data)),
            "calculation_version": VERSION,
        }

    y = data[target_column].to_numpy(dtype=float)
    x = features.to_numpy(dtype=float)
    a = anchors.to_numpy(dtype=float)
    split = max(20, min(len(data) - 8, int(len(data) * 0.70)))
    x_train, x_test = x[:split], x[split:]
    y_train, y_test = y[:split], y[split:]
    a_train = a[:split]
    base_beta = _ridge_fit(x_train, y_train)
    tx, ty = _anchor_transform(x_train, y_train, a_train, gamma=max(1.0, gamma))
    anchor_beta = _ridge_fit(tx, ty)
    base_loss = float(np.mean((_predict(x_test, base_beta) - y_test) ** 2))
    anchor_loss = float(np.mean((_predict(x_test, anchor_beta) - y_test) ** 2))
    coefficient_distance = float(np.linalg.norm(anchor_beta[1:] - base_beta[1:]) / (np.linalg.norm(base_beta[1:]) + 1e-12))
    coefficient_stability = float(max(0.0, 1.0 - min(1.0, coefficient_distance)))
    anchor_penalty = float(max(0.0, anchor_loss - base_loss))

    leave_out: dict[str, Any] = {}
    losses = [anchor_loss]
    for anchor_name in available_anchors:
        levels = data[anchor_name].fillna("UNKNOWN").astype(str)
        level_counts = levels.value_counts()
        candidates = [level for level, count in level_counts.items() if count >= 5]
        if not candidates:
            continue
        test_level = str(candidates[-1])
        train_mask = levels.ne(test_level).to_numpy()
        test_mask = ~train_mask
        if train_mask.sum() < 20 or test_mask.sum() < 5:
            continue
        beta = _ridge_fit(x[train_mask], y[train_mask])
        loss = float(np.mean((_predict(x[test_mask], beta) - y[test_mask]) ** 2))
        losses.append(loss)
        leave_out[anchor_name] = {"held_out_level": test_level, "sample_count": int(test_mask.sum()), "loss": loss}

    worst_case_loss = float(max(losses))
    scale = float(np.var(y_test) + 1e-12)
    relative_worst = worst_case_loss / scale
    score = 100.0 * max(0.0, min(1.0, 0.55 * coefficient_stability + 0.45 * math.exp(-relative_worst)))
    grade = "A" if score >= 80 else ("B" if score >= 65 else ("C" if score >= 50 else "D"))
    unsupported = bool(missing_anchors or not leave_out)
    return {
        "status": "PASS" if score >= 60 and not unsupported else ("INCONCLUSIVE" if score >= 50 else "FAIL"),
        "anchor_robustness_score": float(score), "anchor_penalty": anchor_penalty,
        "worst_case_loss": worst_case_loss, "baseline_holdout_loss": base_loss,
        "anchor_holdout_loss": anchor_loss, "coefficient_stability": coefficient_stability,
        "coefficient_contributions": {name: float(value) for name, value in zip(available_features, anchor_beta[1:])},
        "leave_anchor_level_out": leave_out, "robustness_grade": grade,
        "unsupported_shift_warning": unsupported, "available_anchors": available_anchors,
        "missing_anchors": missing_anchors, "available_features": available_features,
        "sample_count": int(len(data)), "gamma": float(max(1.0, gamma)),
        "claim_boundary": "Robustness only for shifts spanned by logged pre-decision anchors; no causal discovery claim.",
        "calculation_version": VERSION,
    }


__all__ = ["VERSION", "DEFAULT_ANCHORS", "DEFAULT_FEATURES", "evaluate_anchor_robustness"]
