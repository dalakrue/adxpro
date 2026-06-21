"""Consolidated fail-closed production-promotion guard.

The guard is called exactly once per completed Settings Run Calculation.  It
consumes immutable canonical outputs, logs prospective policy evidence, and
publishes one bounded safety object.  It never recalculates or overwrites the
canonical BUY/SELL/WAIT decision or Full Metric history.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import copy
import json
import math
import time

import pandas as pd

from services.canonical_snapshot_store import DB_PATH
from core.research_validation_common_20260621 import stable_hash, utc_now_iso
from core.research_validation_store_20260621 import BUNDLE_KEY
from core.policy_decision_ledger_20260621 import build_policy_ledger_rows, validate_ledger_point_in_time
from core.off_policy_evaluation_20260621 import evaluate_off_policy_safety
from core.anchor_robustness_20260621 import evaluate_anchor_robustness
from core.hsmm_duration_validator_20260621 import evaluate_hsmm_duration
from core.tail_and_drawdown_risk_20260621 import evaluate_tail_and_drawdown
from core.promotion_registry_20260621 import (
    build_state_row, latest_promotion_state, stable_checksum, transition_promotion_state,
)

VERSION = "production-promotion-guard-20260621-v1"
CONFIG_PATH = Path(__file__).resolve().parent / "config" / "production_promotion_guard_limits_20260621.json"
QA_ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "promotion_guard_qa_20260621.json"
OUTPUT_FIELDS = (
    "promotion_status", "promotion_level", "support_coverage", "overlap_status",
    "hcope_lower_bound", "doubly_robust_value", "importance_weight_diagnostics",
    "anchor_robustness_score", "regime_duration_distribution", "regime_transition_hazard",
    "var_es_joint_score", "es_backtest_status", "cvar_95", "cvar_99", "cdar_95",
    "drawdown_probability_bound", "risk_multiplier", "confidence_adjustment",
    "priority_adjustment", "wait_veto", "blocking_reasons", "baseline_version",
    "candidate_version", "evidence_timestamp",
)


def _m(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _path(source: Mapping[str, Any], paths: tuple[str, ...], default: Any = None) -> Any:
    for path in paths:
        current: Any = source
        ok = True
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                ok = False
                break
            current = current[part]
        if ok and current not in (None, ""):
            return current
    return default


def _finite(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def load_guard_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    defaults = {
        "confidence_target": 0.95, "max_policy_deviation": 0.25, "weight_clip": 20.0,
        "hcope_reward_bound": 0.10,
        "min_effective_sample_size": 30.0, "max_weight_share": 0.20,
        "max_estimator_disagreement": 0.002, "minimum_anchor_robustness_score": 60.0,
        "maximum_hsmm_overstay_risk": 0.90, "cvar_95_limit": 0.02,
        "cvar_99_limit": 0.04, "cdar_95_limit": 0.15,
        "drawdown_probability_limit": 0.05, "wealth_floor": 0.80,
        "hard_exposure_cap": 0.25, "minimum_tail_events": 5,
        "maximum_calculation_cpu_seconds": 15.0, "maximum_rss_mb": 1536.0,
        "minimum_support_coverage": 0.80, "hcope_minimum_lower_bound": 0.0,
        "artifact_schema": VERSION,
    }
    try:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(loaded, Mapping):
            defaults.update(dict(loaded))
    except Exception:
        defaults["config_load_failure"] = True
    return defaults


def _existing_multiplier(canonical: Mapping[str, Any]) -> float | None:
    return _finite(_path(canonical, (
        "research_risk_stack.risk_multiplier.display_risk_multiplier",
        "research_risk_stack.display_risk_multiplier",
        "research_risk_stack.risk_multiplier",
        "risk_multiplier.display_risk_multiplier", "risk_multiplier",
    )))


def _boolean_gate(value: Any) -> bool:
    if value is True or value == 1:
        return True
    text = str(value or "").upper().strip()
    return text in {"PASS", "PASSED", "VALID", "SUPPORTED", "EVALUATED", "READY", "TRUE"}


def _existing_research_gates(canonical: Mapping[str, Any]) -> dict[str, bool]:
    research = _m(canonical.get("research_validation_20260621"))
    calibration = _m(canonical.get("research_calibration"))
    ten = _m(canonical.get("ten_paper_research_20260621"))

    pbo = _m(_path(canonical, ("pbo", "research_calibration.pbo", "research.pbo", "reliability.pbo"), {}))
    pbo_value = _finite(pbo.get("value"))
    pbo_pass = str(pbo.get("status") or "").upper() == "VALID" and pbo_value is not None and pbo_value <= 0.25

    dsr = _m(_path(canonical, ("dsr", "research_calibration.dsr", "research.dsr", "reliability.dsr"), {}))
    dsr_probability = _finite(dsr.get("deflated_sharpe_probability"))
    dsr_pass = str(dsr.get("validation_label") or "").upper() == "ACCEPT" or (
        dsr_probability is not None and dsr_probability >= 0.95
    )

    spa_raw = _path(canonical, (
        "research_validation_20260621.superior_predictive_ability",
        "research_validation_20260621.spa", "research.spa",
    ), [])
    spa_items = spa_raw if isinstance(spa_raw, list) else [spa_raw]
    spa_evaluable = [item for item in spa_items if isinstance(item, Mapping)]
    spa_pass = bool(spa_evaluable) and any(
        _boolean_gate(item.get("promotion_allowed"))
        or _boolean_gate(item.get("stability_pass"))
        or _boolean_gate(_m(item.get("row")).get("promotion_allowed"))
        for item in spa_evaluable
    )

    fdr = _m(_path(canonical, (
        "ten_paper_research_20260621.paper_2",
        "ten_paper_research_20260621.online_fdr",
        "research_validation_20260621.online_fdr", "online_fdr",
    ), {}))
    fdr_pass = _boolean_gate(fdr.get("gate_pass") or fdr.get("status") or fdr.get("promotion_allowed"))
    evidence_gates = _m(ten.get("evidence_gates"))
    named_gates = _m(evidence_gates.get("gates"))
    for gate_name, gate_value in named_gates.items():
        if "fdr" in str(gate_name).lower():
            fdr_pass = fdr_pass and bool(_m(gate_value).get("pass")) if fdr_pass else bool(_m(gate_value).get("pass"))

    return {
        "existing_pbo_gate": bool(pbo_pass),
        "existing_deflated_sharpe_gate": bool(dsr_pass),
        "existing_spa_predictive_ability_gate": bool(spa_pass),
        "existing_online_fdr_gate": bool(fdr_pass),
        "existing_research_bundle_present": bool(research and calibration and ten),
    }


def _artifact_checksum(config: Mapping[str, Any]) -> str:
    module_names = (
        "production_promotion_guard_20260621.py", "policy_decision_ledger_20260621.py",
        "off_policy_evaluation_20260621.py", "anchor_robustness_20260621.py",
        "hsmm_duration_validator_20260621.py", "tail_and_drawdown_risk_20260621.py",
        "promotion_registry_20260621.py",
    )
    root = Path(__file__).resolve().parent
    hashes = {}
    for name in module_names:
        path = root / name
        hashes[name] = stable_hash(path.read_bytes()) if path.exists() else "MISSING"
    return stable_checksum({"modules": hashes, "config": dict(config), "version": VERSION})



def _database_integrity(db_path: Path | str) -> bool:
    path = Path(db_path)
    if not path.exists():
        return True
    import sqlite3
    connection = None
    try:
        connection = sqlite3.connect(str(path), timeout=5, check_same_thread=False)
        row = connection.execute("PRAGMA quick_check").fetchone()
        return bool(row and str(row[0]).lower() == "ok")
    except Exception:
        return False
    finally:
        if connection is not None:
            connection.close()


def _verified_qa_gates(artifact_checksum: str) -> dict[str, bool]:
    try:
        artifact = json.loads(QA_ARTIFACT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"deterministic_rerun_test": False, "rollback_test": False}
    valid = (
        isinstance(artifact, Mapping)
        and artifact.get("artifact_checksum") == artifact_checksum
        and artifact.get("schema_version") == 1
    )
    return {
        "deterministic_rerun_test": bool(valid and artifact.get("deterministic_rerun_pass") is True),
        "rollback_test": bool(valid and artifact.get("rollback_test_pass") is True),
    }

def _row(source_generation_id: str, prefix: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.setdefault("source_generation_id", source_generation_id)
    result.setdefault("evaluated_at", utc_now_iso())
    result.setdefault("calculation_version", VERSION)
    result.setdefault("record_key", f"{prefix}-" + stable_hash([source_generation_id, prefix, result])[:24])
    return result


def _fail_closed_output(canonical: Mapping[str, Any], reasons: list[str], *, timestamp: str | None = None) -> dict[str, Any]:
    baseline = str(_path(canonical, ("calculation_version", "metadata.calculation_version", "model_version"), "canonical-baseline"))
    candidate = str(_path(canonical, ("shadow_policy.version", "candidate_version"), "shadow-candidate-v1"))
    output = {
        "promotion_status": "BLOCKED_FAIL_CLOSED", "promotion_level": "BLOCKED",
        "support_coverage": 0.0, "overlap_status": "NOT_IDENTIFIABLE",
        "hcope_lower_bound": None, "doubly_robust_value": None,
        "importance_weight_diagnostics": {"status": "NOT_IDENTIFIABLE"},
        "anchor_robustness_score": None, "regime_duration_distribution": {},
        "regime_transition_hazard": None, "var_es_joint_score": None,
        "es_backtest_status": "INSUFFICIENT_EVIDENCE", "cvar_95": None,
        "cvar_99": None, "cdar_95": None, "drawdown_probability_bound": None,
        "risk_multiplier": 0.0, "confidence_adjustment": 0.0,
        "priority_adjustment": 0.0, "wait_veto": False,
        "blocking_reasons": sorted(set(str(reason) for reason in reasons if str(reason))),
        "baseline_version": baseline, "candidate_version": candidate,
        "evidence_timestamp": timestamp or utc_now_iso(),
    }
    return {key: output[key] for key in OUTPUT_FIELDS}


def build_production_promotion_guard_transaction(
    canonical: Mapping[str, Any],
    *,
    completed_h1: pd.DataFrame,
    previous: Mapping[str, Any] | None = None,
    runtime_metrics: Mapping[str, Any] | None = None,
    db_path: Path | str = DB_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    payload = copy.deepcopy(dict(canonical or {}))
    config = load_guard_config()
    evaluated_at = utc_now_iso()
    source_generation_id = str(payload.get("canonical_calculation_id") or payload.get("run_id") or payload.get("calculation_generation") or "UNKNOWN")
    hard_failures: list[str] = []
    rollback_failures: list[str] = []
    if str(payload.get("symbol") or "EURUSD").upper() != "EURUSD": hard_failures.append("SYMBOL_NOT_EURUSD")
    if str(payload.get("timeframe") or "H1").upper() != "H1": hard_failures.append("TIMEFRAME_NOT_H1")
    if config.get("config_load_failure"): hard_failures.append("RISK_LIMIT_CONFIG_LOAD_FAILURE")
    if int(config.get("schema_version", 0) or 0) != 1: hard_failures.append("UNKNOWN_PROMOTION_SCHEMA_VERSION")
    if bool(_m(payload.get("metadata")).get("stale") or payload.get("stale")): hard_failures.append("RESEARCH_OUTPUTS_STALE")

    ledger_rows, combined_ledger, ledger_diagnostic = build_policy_ledger_rows(payload, completed_h1, db_path=db_path)
    current_ledger = ledger_rows[-1] if ledger_rows else {}
    required_current = (
        current_ledger.get("data_cutoff_timestamp"), current_ledger.get("reference_entry_price"),
        current_ledger.get("baseline_action"), current_ledger.get("feature_snapshot_hash"),
    )
    if not all(value not in (None, "") for value in required_current):
        hard_failures.append("REQUIRED_POINT_IN_TIME_FEATURES_MISSING")
    raw_existing_multiplier = _path(payload, (
        "research_risk_stack.risk_multiplier.display_risk_multiplier",
        "research_risk_stack.display_risk_multiplier", "risk_multiplier.display_risk_multiplier",
    ))
    if raw_existing_multiplier not in (None, "") and _finite(raw_existing_multiplier) is None:
        hard_failures.append("NON_FINITE_EXISTING_RISK_VALUE")
    pit = validate_ledger_point_in_time(combined_ledger)
    if not pit.get("valid"): hard_failures.append("POINT_IN_TIME_OR_SETTLEMENT_VALIDATION_FAILED")
    one_hour = combined_ledger.copy()
    if not one_hour.empty and "evaluation_horizon" in one_hour.columns:
        one_hour = one_hour.loc[pd.to_numeric(one_hour["evaluation_horizon"], errors="coerce").eq(1)].copy()
    settled = one_hour.loc[one_hour.get("record_status", pd.Series("", index=one_hour.index)).astype(str).str.upper().eq("SETTLED")].copy() if not one_hour.empty else pd.DataFrame()

    off_policy = evaluate_off_policy_safety(
        settled, confidence_target=float(config["confidence_target"]),
        max_policy_deviation=float(config["max_policy_deviation"]),
        weight_clip=float(config["weight_clip"]),
        reward_bound=float(config["hcope_reward_bound"]),
    )
    spibb = _m(off_policy.get("spibb")); hcope = _m(off_policy.get("hcope")); dr = _m(off_policy.get("doubly_robust"))
    anchor = evaluate_anchor_robustness(settled)
    hsmm_source = one_hour if not one_hour.empty else pd.DataFrame()
    hsmm = evaluate_hsmm_duration(hsmm_source)
    tail = evaluate_tail_and_drawdown(
        settled, existing_multiplier=_existing_multiplier(payload),
        exposure_cap=float(config["hard_exposure_cap"]),
        cvar_95_limit=float(config["cvar_95_limit"]), cvar_99_limit=float(config["cvar_99_limit"]),
        cdar_95_limit=float(config["cdar_95_limit"]),
        drawdown_probability_limit=float(config["drawdown_probability_limit"]),
        wealth_floor=float(config["wealth_floor"]), min_tail_events=int(config["minimum_tail_events"]),
        blocked=bool(hard_failures),
    )

    metrics = dict(runtime_metrics or {})
    cpu_seconds = _finite(metrics.get("calculation_cpu_seconds") or metrics.get("cpu_seconds"))
    latency_ms = _finite(metrics.get("calculation_latency_ms"))
    rss_mb = _finite(metrics.get("rss_mb"))
    resource_pass = not (
        (cpu_seconds is not None and cpu_seconds > float(config["maximum_calculation_cpu_seconds"]))
        or (latency_ms is not None and latency_ms > float(config["maximum_calculation_cpu_seconds"]) * 1000.0)
        or (rss_mb is not None and rss_mb > float(config["maximum_rss_mb"]))
    )
    if not resource_pass: hard_failures.append("RESOURCE_BUDGET_EXCEEDED")

    existing_gates = _existing_research_gates(payload)
    disagreement = _finite(dr.get("estimator_disagreement"))
    artifact_checksum = _artifact_checksum(config)
    previous_state = latest_promotion_state(db_path=db_path)
    previous_level = previous_state.get("promotion_level") or "SHADOW"
    previous_checksum = previous_state.get("artifact_checksum")
    qa_gates = _verified_qa_gates(artifact_checksum)
    database_integrity = _database_integrity(db_path)
    if not database_integrity: hard_failures.append("DATABASE_INTEGRITY_FAILED")
    if previous_level in {"RISK_ONLY", "LIMITED_PRODUCTION", "FULL_RISK_PROMOTION"} and previous_checksum and previous_checksum != artifact_checksum:
        rollback_failures.append("PROMOTION_ARTIFACT_CHECKSUM_DIFFERS")

    gates: dict[str, bool] = {
        "point_in_time_data_validation": bool(pit.get("valid")),
        "no_future_leakage": not bool(ledger_diagnostic.get("future_leakage_detected")),
        "outcome_settlement_validation": bool(pit.get("valid")),
        "adequate_support": float(spibb.get("support_coverage") or 0.0) >= float(config["minimum_support_coverage"]) and not bool(spibb.get("baseline_bootstrap_required")),
        "adequate_overlap": hcope.get("status") == "EVALUATED",
        "hcope_lower_bound_gate": _finite(hcope.get("lower_confidence_bound")) is not None and float(hcope.get("lower_confidence_bound")) >= float(config["hcope_minimum_lower_bound"]),
        "doubly_robust_agreement": dr.get("status") == "EVALUATED" and disagreement is not None and disagreement <= float(config["max_estimator_disagreement"]),
        "anchor_robustness": anchor.get("status") == "PASS" and float(anchor.get("anchor_robustness_score") or 0.0) >= float(config["minimum_anchor_robustness_score"]),
        "hsmm_stability": hsmm.get("status") == "PASS" and float(hsmm.get("overstay_risk") or 1.0) <= float(config["maximum_hsmm_overstay_risk"]),
        "var_es_scoring": _finite(tail.get("var_es_joint_score")) is not None,
        "es_backtesting": tail.get("es_backtest_status") == "PASS",
        "cvar_limits": tail.get("cvar_95") is not None and tail.get("cvar_99") is not None and float(tail["cvar_95"]) <= float(config["cvar_95_limit"]) and float(tail["cvar_99"]) <= float(config["cvar_99_limit"]),
        "cdar_limits": tail.get("cdar_95") is not None and float(tail["cdar_95"]) <= float(config["cdar_95_limit"]),
        "drawdown_probability_limit": tail.get("drawdown_probability_bound") is not None and float(tail["drawdown_probability_bound"]) <= float(config["drawdown_probability_limit"]),
        "resource_budget": resource_pass,
        "database_integrity": database_integrity,
        "deterministic_rerun_test": qa_gates["deterministic_rerun_test"],
        "rollback_test": qa_gates["rollback_test"],
        **existing_gates,
    }
    insufficient_markers = {
        "NO_SETTLED_POLICY_LEDGER", "NO_COST_COMPLETE_SETTLED_OUTCOMES",
        "MISSING_LOGGED_PROPENSITY_OR_NET_RETURN", "INSUFFICIENT_CHRONOLOGICAL_ROWS",
        "LOW_SPIBB_SUPPORT", "PROPENSITY_ABSENT",
    }
    failure_reasons = list(off_policy.get("failure_reason") or [])
    insufficient = bool(settled.empty or any(
        reason in insufficient_markers or "INSUFFICIENT" in str(reason) or "MISSING" in str(reason)
        for reason in failure_reasons
    ))
    # Deterministic and rollback gates remain closed until their packaged tests
    # produce a verified artifact; adding code alone never promotes influence.
    transition = transition_promotion_state(
        previous_level, gates, hard_failures=hard_failures,
        rollback_failures=rollback_failures, insufficient_evidence=insufficient,
    )
    blocking = list(dict.fromkeys(list(transition.blocking_reasons) + failure_reasons + list(tail.get("tail_risk_breach_reason") or [])))
    influence_enabled = transition.promotion_level == "FULL_RISK_PROMOTION" and transition.all_gates_pass
    safe_risk = float(tail.get("risk_multiplier") or 0.0) if influence_enabled else 0.0
    # Adjustments are non-positive. They are informational until full risk promotion.
    confidence_adjustment = -min(100.0, max(0.0, 100.0 - float(anchor.get("anchor_robustness_score") or 0.0))) if influence_enabled else 0.0
    priority_adjustment = -min(100.0, 100.0 * (1.0 - float(spibb.get("support_coverage") or 0.0))) if influence_enabled else 0.0
    wait_veto = bool(influence_enabled and (tail.get("status") == "BLOCKED" or safe_risk <= 0.0))
    baseline_version = str(ledger_rows[-1].get("baseline_version") if ledger_rows else _path(payload, ("calculation_version",), "canonical-baseline"))
    candidate_version = str(ledger_rows[-1].get("candidate_version") if ledger_rows else _path(payload, ("candidate_version",), "shadow-candidate-v1"))
    guard = {
        "promotion_status": transition.promotion_status,
        "promotion_level": transition.promotion_level,
        "support_coverage": float(spibb.get("support_coverage") or 0.0),
        "overlap_status": str(hcope.get("ope_status") or hcope.get("status") or "NOT_IDENTIFIABLE"),
        "hcope_lower_bound": _finite(hcope.get("lower_confidence_bound")),
        "doubly_robust_value": _finite(dr.get("doubly_robust_value")),
        "importance_weight_diagnostics": {
            "raw_sample_count": hcope.get("raw_sample_count"),
            "effective_sample_size": hcope.get("effective_sample_size"),
            "maximum_importance_weight": hcope.get("maximum_importance_weight"),
            "weight_concentration": hcope.get("weight_concentration"),
            "clipped_estimate": hcope.get("clipped_estimate"),
            "unclipped_estimate": hcope.get("unclipped_estimate"),
            "estimator_disagreement": disagreement,
            "failure_reason": hcope.get("failure_reason") or [],
        },
        "anchor_robustness_score": _finite(anchor.get("anchor_robustness_score")),
        "regime_duration_distribution": hsmm.get("regime_duration_distribution") or {},
        "regime_transition_hazard": _finite(hsmm.get("regime_transition_hazard")),
        "var_es_joint_score": _finite(tail.get("var_es_joint_score")),
        "es_backtest_status": str(tail.get("es_backtest_status") or "INSUFFICIENT_EVIDENCE"),
        "cvar_95": _finite(tail.get("cvar_95")), "cvar_99": _finite(tail.get("cvar_99")),
        "cdar_95": _finite(tail.get("cdar_95")),
        "drawdown_probability_bound": _finite(tail.get("drawdown_probability_bound")),
        "risk_multiplier": safe_risk, "confidence_adjustment": float(confidence_adjustment),
        "priority_adjustment": float(priority_adjustment), "wait_veto": wait_veto,
        "blocking_reasons": blocking, "baseline_version": baseline_version,
        "candidate_version": candidate_version, "evidence_timestamp": evaluated_at,
    }
    guard = {key: guard[key] for key in OUTPUT_FIELDS}
    payload["production_promotion_guard_20260621"] = guard
    payload.setdefault("metadata", {})["production_promotion_guard_version"] = VERSION
    payload["metadata"]["production_promotion_guard_direction_policy"] = "confirm/reduce/WAIT-veto only; no directional authority"

    state_row = build_state_row(
        source_generation_id=source_generation_id, transition=transition,
        gate_results=gates, artifact_checksum=artifact_checksum, evaluated_at=evaluated_at,
    )
    hcope_row = _row(source_generation_id, "HCOPE", {
        "estimator": "HCOPE", "status": hcope.get("status"),
        "raw_sample_count": hcope.get("raw_sample_count"),
        "effective_sample_size": hcope.get("effective_sample_size"),
        "support_coverage": hcope.get("support_coverage"),
        "lower_confidence_bound": hcope.get("lower_confidence_bound"),
        "estimate": hcope.get("clipped_estimate"),
        "promotion_allowed": hcope.get("policy_promotion_allowed"),
        "failure_reason": ",".join(hcope.get("failure_reason") or []),
    })
    dr_row = _row(source_generation_id, "DR", {
        "estimator": "DOUBLY_ROBUST", "status": dr.get("status"),
        "raw_sample_count": dr.get("sample_count"), "estimate": dr.get("doubly_robust_value"),
        "promotion_allowed": dr.get("status") == "EVALUATED",
        "failure_reason": ",".join(dr.get("failure_reason") or []),
    })
    bundle = {BUNDLE_KEY: {
        "policy_decision_ledger_20260621": ledger_rows,
        "off_policy_evaluation_20260621": [hcope_row, dr_row],
        "anchor_robustness_history_20260621": [_row(source_generation_id, "ANCHOR", anchor)],
        "hsmm_duration_history_20260621": [_row(source_generation_id, "HSMM", hsmm)],
        "tail_drawdown_risk_history_20260621": [_row(source_generation_id, "TAIL", tail)],
        "promotion_state_history_20260621": [state_row],
        "production_promotion_guard_history_20260621": [_row(source_generation_id, "GUARD", guard)],
    }}
    summary = {
        "version": VERSION, "promotion_status": guard["promotion_status"],
        "promotion_level": guard["promotion_level"], "blocking_reasons": guard["blocking_reasons"],
        "settled_1h_evidence_rows": int(len(settled)), "ledger_rows_staged": int(len(ledger_rows)),
        "all_gates_pass": transition.all_gates_pass, "production_influence_enabled": influence_enabled,
        "artifact_checksum": artifact_checksum, "duration_ms": (time.perf_counter() - started) * 1000.0,
        "protected_direction_unchanged": True, "full_metric_history_unchanged": True,
    }
    return payload, bundle, summary


__all__ = [
    "VERSION", "CONFIG_PATH", "QA_ARTIFACT_PATH", "OUTPUT_FIELDS", "load_guard_config",
    "build_production_promotion_guard_transaction", "_fail_closed_output",
]
