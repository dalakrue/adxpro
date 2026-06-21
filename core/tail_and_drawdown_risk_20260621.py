"""Point-in-time tail risk, ES backtesting, CDaR and constrained sizing.

Only settled, cost-complete chronological ledger outcomes are used.  The module
can reduce or zero an existing risk multiplier; it cannot increase it beyond an
existing stricter cap and has no directional authority.
"""
from __future__ import annotations

from typing import Any, Mapping
import math

import numpy as np
import pandas as pd

VERSION = "tail-drawdown-risk-20260621-v1"


def _finite(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _clean_settled(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    data = frame.copy()
    status = data.get("record_status", pd.Series("", index=data.index)).astype(str).str.upper()
    data = data.loc[status.eq("SETTLED")].copy()
    data["net_return_fraction"] = pd.to_numeric(data.get("net_return_fraction"), errors="coerce")
    data = data.loc[data["net_return_fraction"].notna()].copy()
    for name in ("settlement_timestamp", "decision_timestamp_utc", "evaluated_at"):
        if name in data.columns:
            data["__time"] = pd.to_datetime(data[name], errors="coerce", utc=True)
            if data["__time"].notna().any():
                data = data.loc[data["__time"].notna()].sort_values("__time", kind="mergesort")
                break
    return data.reset_index(drop=True)


def empirical_var_es(losses: np.ndarray, alpha: float) -> tuple[float | None, float | None, int]:
    values = np.asarray(losses, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return None, None, 0
    a = min(0.999, max(0.50, float(alpha)))
    var = float(np.quantile(values, a, method="higher"))
    tail = values[values >= var]
    es = float(tail.mean()) if len(tail) else var
    return var, max(var, es), int(len(tail))


def fissler_ziegel_joint_score(loss: float, var: float, es: float, alpha: float = 0.95) -> float:
    """A finite FZ0-equivalent score on losses for relative model ranking.

    We evaluate the standard FZ0 score on returns Y=-loss with lower-tail
    forecasts q=-VaR and e=-ES.  It is strictly consistent on the corrected
    action domain q>=e, e<0.  Additive observation-only terms are omitted.
    """
    if not all(math.isfinite(float(x)) for x in (loss, var, es, alpha)):
        return math.nan
    a = min(0.999, max(0.001, 1.0 - float(alpha)))
    y, q, e = -float(loss), -float(var), -float(es)
    if e >= -1e-12 or q < e - 1e-12:
        return math.nan
    indicator = 1.0 if y <= q else 0.0
    return float(-math.log(-e) - ((indicator * (q - y)) / (a * e)) + (q / e) - 1.0)


def _point_in_time_forecasts(losses: np.ndarray, alpha: float, min_train: int, window: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index in range(min_train, len(losses)):
        start = max(0, index - window)
        train = losses[start:index]
        var, es, _ = empirical_var_es(train, alpha)
        if var is None or es is None:
            continue
        observed = float(losses[index])
        rows.append({
            "index": index, "loss": observed, "var": var, "es": es,
            "breach": observed > var,
            "joint_score": fissler_ziegel_joint_score(observed, var, es, alpha),
            "es_residual": (observed - es) if observed > var else 0.0,
        })
    return pd.DataFrame(rows)


def _normal_two_sided_p(statistic: float) -> float:
    return float(math.erfc(abs(float(statistic)) / math.sqrt(2.0)))


def evaluate_es_backtest(
    losses: np.ndarray,
    *,
    alpha: float = 0.95,
    min_train: int = 30,
    window: int = 500,
    min_tail_events: int = 5,
) -> dict[str, Any]:
    forecasts = _point_in_time_forecasts(np.asarray(losses, dtype=float), alpha, min_train, window)
    if forecasts.empty:
        return {
            "status": "INSUFFICIENT_EVIDENCE", "unconditional_status": "INSUFFICIENT_EVIDENCE",
            "conditional_status": "INSUFFICIENT_EVIDENCE", "tail_event_count": 0,
            "tail_event_severity": None, "too_few_events": True,
            "var_es_joint_score": None, "forecast_count": 0,
        }
    breaches = forecasts.loc[forecasts["breach"]]
    tail_count = int(len(breaches))
    residuals = forecasts["es_residual"].to_numpy(dtype=float)
    unconditional_se = float(np.std(residuals, ddof=1) / math.sqrt(len(residuals))) if len(residuals) > 1 else math.inf
    unconditional_stat = float(np.mean(residuals) / unconditional_se) if unconditional_se > 0 and math.isfinite(unconditional_se) else 0.0
    unconditional_p = _normal_two_sided_p(unconditional_stat)
    # Conditional calibration: test ES residual association with lagged breach.
    if len(forecasts) >= 3:
        lag = forecasts["breach"].astype(float).shift(1).fillna(0.0).to_numpy()
        centered = lag - lag.mean()
        moment = centered * residuals
        se = float(np.std(moment, ddof=1) / math.sqrt(len(moment))) if len(moment) > 1 else math.inf
        conditional_stat = float(np.mean(moment) / se) if se > 0 and math.isfinite(se) else 0.0
        conditional_p = _normal_two_sided_p(conditional_stat)
    else:
        conditional_stat, conditional_p = 0.0, 1.0
    too_few = tail_count < int(max(1, min_tail_events))
    uncond_status = "INCONCLUSIVE" if too_few else ("PASS" if unconditional_p >= 0.05 else "REJECTED")
    cond_status = "INCONCLUSIVE" if too_few else ("PASS" if conditional_p >= 0.05 else "REJECTED")
    overall = "TOO_FEW_EVENTS" if too_few else ("PASS" if uncond_status == cond_status == "PASS" else "REJECTED")
    severity = float(np.mean(breaches["loss"] - breaches["es"])) if tail_count else None
    return {
        "status": overall, "unconditional_status": uncond_status,
        "conditional_status": cond_status, "unconditional_statistic": unconditional_stat,
        "unconditional_p_value": unconditional_p, "conditional_statistic": conditional_stat,
        "conditional_p_value": conditional_p, "tail_event_count": tail_count,
        "tail_event_severity": severity, "too_few_events": too_few,
        "var_es_joint_score": float(pd.to_numeric(forecasts["joint_score"], errors="coerce").dropna().mean()) if forecasts["joint_score"].notna().any() else None,
        "forecast_count": int(len(forecasts)),
        "interpretation": "Relative FZ score and absolute ES moment backtests are reported separately.",
    }


def drawdown_statistics(returns: np.ndarray, alpha: float = 0.95) -> dict[str, Any]:
    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {
            "current_drawdown": None, "maximum_drawdown": None, "average_drawdown": None,
            "cdar": None, "underwater_duration": 0, "maximum_underwater_duration": 0,
            "recovery_duration": None, "loss_cluster_length": 0,
        }
    wealth = np.cumprod(np.maximum(1e-9, 1.0 + values))
    peaks = np.maximum.accumulate(np.r_[1.0, wealth])[:-1]
    drawdown = np.maximum(0.0, 1.0 - wealth / np.maximum(peaks, 1e-12))
    q = float(np.quantile(drawdown, min(0.999, max(0.50, alpha)), method="higher"))
    tail = drawdown[drawdown >= q]
    underwater = drawdown > 1e-15
    current_run = 0
    max_run = 0
    completed_runs: list[int] = []
    for flag in underwater:
        if flag:
            current_run += 1
            max_run = max(max_run, current_run)
        elif current_run:
            completed_runs.append(current_run)
            current_run = 0
    loss_run = 0
    for ret in values[::-1]:
        if ret < 0:
            loss_run += 1
        else:
            break
    return {
        "current_drawdown": float(drawdown[-1]), "maximum_drawdown": float(drawdown.max()),
        "average_drawdown": float(drawdown.mean()), "cdar": float(tail.mean()) if len(tail) else q,
        "underwater_duration": int(current_run), "maximum_underwater_duration": int(max_run),
        "recovery_duration": float(np.mean(completed_runs)) if completed_runs else None,
        "loss_cluster_length": int(loss_run), "equity_terminal": float(wealth[-1]),
    }


def constrained_kelly_multiplier(
    returns: np.ndarray,
    *,
    existing_multiplier: float | None,
    exposure_cap: float,
    wealth_floor: float = 0.80,
    drawdown_probability_limit: float = 0.05,
    cvar_95: float | None = None,
    cvar_limit: float = 0.02,
    cdar_95: float | None = None,
    cdar_limit: float = 0.15,
    blocked: bool = False,
) -> dict[str, Any]:
    existing = 1.0 if existing_multiplier is None else max(0.0, min(1.0, float(existing_multiplier)))
    cap = max(0.0, min(1.0, float(exposure_cap), existing))
    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if blocked or len(values) < 20:
        return {"risk_multiplier": 0.0, "raw_kelly_fraction": None, "risk_constrained_fraction": 0.0,
                "drawdown_probability_bound": None, "status": "BLOCKED" if blocked else "INSUFFICIENT_EVIDENCE"}
    mean = float(values.mean())
    variance = float(values.var(ddof=1)) if len(values) > 1 else 0.0
    raw = max(0.0, min(1.0, mean / max(1e-12, variance)))
    alpha_wealth = min(0.999, max(0.01, float(wealth_floor)))
    beta = min(0.50, max(1e-6, float(drawdown_probability_limit)))
    lam = math.log(beta) / math.log(alpha_wealth)
    feasible = 0.0
    for fraction in np.linspace(0.0, cap, 201):
        wealth_factors = 1.0 + fraction * values
        if np.any(wealth_factors <= 0):
            continue
        moment_bound = float(np.mean(np.power(wealth_factors, -lam)))
        if moment_bound <= 1.0 + 1e-12:
            feasible = float(fraction)
    cvar_scale = 1.0 if cvar_95 is None or cvar_95 <= cvar_limit else max(0.0, cvar_limit / max(cvar_95, 1e-12))
    cdar_scale = 1.0 if cdar_95 is None or cdar_95 <= cdar_limit else max(0.0, cdar_limit / max(cdar_95, 1e-12))
    final = min(cap, raw, feasible) * min(1.0, cvar_scale, cdar_scale)
    final = max(0.0, min(existing, cap, final))
    return {
        "risk_multiplier": float(final), "raw_kelly_fraction": raw,
        "risk_constrained_fraction": feasible, "drawdown_probability_bound": beta,
        "wealth_floor": alpha_wealth, "lambda": lam, "existing_multiplier_cap": existing,
        "hard_exposure_cap": cap, "cvar_scale": cvar_scale, "cdar_scale": cdar_scale,
        "status": "PASS" if final > 0 else "ZERO_EXPOSURE",
    }


def evaluate_tail_and_drawdown(
    settled: pd.DataFrame,
    *,
    existing_multiplier: float | None = None,
    exposure_cap: float = 0.25,
    cvar_95_limit: float = 0.02,
    cvar_99_limit: float = 0.04,
    cdar_95_limit: float = 0.15,
    drawdown_probability_limit: float = 0.05,
    wealth_floor: float = 0.80,
    min_tail_events: int = 5,
    blocked: bool = False,
) -> dict[str, Any]:
    data = _clean_settled(settled)
    if data.empty:
        sizing = constrained_kelly_multiplier(np.array([]), existing_multiplier=existing_multiplier,
            exposure_cap=exposure_cap, wealth_floor=wealth_floor,
            drawdown_probability_limit=drawdown_probability_limit, blocked=True)
        return {
            "status": "INSUFFICIENT_EVIDENCE", "var_95": None, "var_99": None,
            "cvar_95": None, "cvar_99": None, "cdar_95": None,
            "var_es_joint_score": None, "es_backtest_status": "INSUFFICIENT_EVIDENCE",
            "tail_event_count": 0, "tail_event_severity": None,
            "tail_risk_breach_reason": ["NO_COST_COMPLETE_SETTLED_OUTCOMES"],
            **sizing, "calculation_version": VERSION,
        }
    returns = data["net_return_fraction"].to_numpy(dtype=float)
    losses = -returns
    var95, es95, tail95 = empirical_var_es(losses, 0.95)
    var99, es99, tail99 = empirical_var_es(losses, 0.99)
    backtest = evaluate_es_backtest(losses, alpha=0.95, min_tail_events=min_tail_events)
    drawdown = drawdown_statistics(returns, 0.95)
    cdar95 = _finite(drawdown.get("cdar"))
    reasons: list[str] = []
    if es95 is not None and es95 > cvar_95_limit: reasons.append("CVAR_95_LIMIT")
    if es99 is not None and es99 > cvar_99_limit: reasons.append("CVAR_99_LIMIT")
    if cdar95 is not None and cdar95 > cdar_95_limit: reasons.append("CDAR_95_LIMIT")
    if backtest["status"] in {"REJECTED", "TOO_FEW_EVENTS", "INSUFFICIENT_EVIDENCE"}: reasons.append("ES_BACKTEST_" + backtest["status"])
    sizing = constrained_kelly_multiplier(
        returns, existing_multiplier=existing_multiplier, exposure_cap=exposure_cap,
        wealth_floor=wealth_floor, drawdown_probability_limit=drawdown_probability_limit,
        cvar_95=es95, cvar_limit=cvar_95_limit, cdar_95=cdar95, cdar_limit=cdar_95_limit,
        blocked=bool(blocked or reasons),
    )
    regime_cdar: dict[str, float] = {}
    if "h1_regime" in data.columns:
        for regime, group in data.groupby(data["h1_regime"].fillna("UNKNOWN").astype(str), sort=True):
            if len(group) >= 5:
                value = drawdown_statistics(group["net_return_fraction"].to_numpy(dtype=float), 0.95).get("cdar")
                if value is not None: regime_cdar[str(regime)] = float(value)
    return {
        "status": "PASS" if not reasons else "BLOCKED", "sample_count": int(len(data)),
        "var_95": var95, "var_99": var99, "cvar_95": es95, "cvar_99": es99,
        "tail_event_count": int(max(tail95, backtest["tail_event_count"])),
        "tail_event_count_99": tail99, "tail_event_severity": backtest["tail_event_severity"],
        "var_es_joint_score": backtest["var_es_joint_score"],
        "es_backtest_status": backtest["status"], "es_backtest": backtest,
        "cdar_95": cdar95, "current_drawdown": drawdown.get("current_drawdown"),
        "maximum_drawdown": drawdown.get("maximum_drawdown"),
        "average_drawdown": drawdown.get("average_drawdown"),
        "underwater_duration": drawdown.get("underwater_duration"),
        "recovery_duration": drawdown.get("recovery_duration"),
        "loss_cluster_length": drawdown.get("loss_cluster_length"),
        "regime_conditioned_cdar": regime_cdar,
        "tail_risk_breach_reason": reasons, **sizing,
        "relative_vs_absolute_boundary": "FZ score ranks forecasts; ES moment tests assess calibration and may be inconclusive.",
        "calculation_version": VERSION,
    }


__all__ = [
    "VERSION", "empirical_var_es", "fissler_ziegel_joint_score", "evaluate_es_backtest",
    "drawdown_statistics", "constrained_kelly_multiplier", "evaluate_tail_and_drawdown",
]
