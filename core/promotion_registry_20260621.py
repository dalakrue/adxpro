"""Fail-closed promotion state registry for the 2026-06-21 safety guard.

The registry never grants directional authority.  It records whether a
read-only risk/promotion guard has enough evidence to influence confidence,
priority, exposure, holding horizon, or a BUY/SELL-to-WAIT veto.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import sqlite3

from services.canonical_snapshot_store import DB_PATH

VERSION = "promotion-registry-20260621-v1"
PROMOTION_STATES = (
    "SHADOW",
    "OBSERVATION",
    "RISK_ONLY",
    "LIMITED_PRODUCTION",
    "FULL_RISK_PROMOTION",
    "DEGRADED",
    "BLOCKED",
    "ROLLED_BACK",
)
_ORDERED = ("SHADOW", "OBSERVATION", "RISK_ONLY", "LIMITED_PRODUCTION", "FULL_RISK_PROMOTION")
_NEXT = {state: _ORDERED[min(index + 1, len(_ORDERED) - 1)] for index, state in enumerate(_ORDERED)}


@dataclass(frozen=True)
class PromotionTransition:
    previous_level: str
    promotion_level: str
    promotion_status: str
    all_gates_pass: bool
    blocking_reasons: tuple[str, ...]
    rollback_required: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "previous_level": self.previous_level,
            "promotion_level": self.promotion_level,
            "promotion_status": self.promotion_status,
            "all_gates_pass": self.all_gates_pass,
            "blocking_reasons": list(self.blocking_reasons),
            "rollback_required": self.rollback_required,
        }


def _normalise_state(value: Any) -> str:
    state = str(value or "SHADOW").upper().strip()
    return state if state in PROMOTION_STATES else "SHADOW"


def stable_checksum(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def latest_promotion_state(*, db_path: Path | str = DB_PATH) -> dict[str, Any]:
    path = Path(db_path)
    if not path.exists():
        return {}
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='promotion_state_history_20260621'"
        ).fetchone()
        if not exists:
            return {}
        row = conn.execute(
            "SELECT payload_json FROM promotion_state_history_20260621 "
            "ORDER BY evaluated_at DESC, record_key DESC LIMIT 1"
        ).fetchone()
        return json.loads(row[0]) if row and row[0] else {}
    except Exception:
        return {}
    finally:
        if conn is not None:
            conn.close()


def transition_promotion_state(
    previous_level: Any,
    gates: Mapping[str, Any],
    *,
    hard_failures: list[str] | tuple[str, ...] = (),
    rollback_failures: list[str] | tuple[str, ...] = (),
    insufficient_evidence: bool = False,
) -> PromotionTransition:
    """Advance at most one stage, or fail closed.

    A state is never skipped.  A prior production state is degraded or rolled
    back when mandatory safety evidence fails.  BLOCKED/ROLLED_BACK can only
    return to SHADOW through an explicit subsequent clean evaluation.
    """
    previous = _normalise_state(previous_level)
    failed = sorted(str(name) for name, passed in gates.items() if passed is not True)
    hard = sorted({str(x) for x in hard_failures if str(x)})
    rollback = sorted({str(x) for x in rollback_failures if str(x)})
    reasons = tuple(dict.fromkeys(rollback + hard + failed))

    if rollback:
        return PromotionTransition(previous, "ROLLED_BACK", "ROLLED_BACK_SAFETY_FAILURE", False, reasons, True)
    if hard:
        level = "DEGRADED" if previous in {"RISK_ONLY", "LIMITED_PRODUCTION", "FULL_RISK_PROMOTION"} else "BLOCKED"
        return PromotionTransition(previous, level, "BLOCKED_FAIL_CLOSED", False, reasons)
    if insufficient_evidence or failed:
        level = "DEGRADED" if previous in {"RISK_ONLY", "LIMITED_PRODUCTION", "FULL_RISK_PROMOTION"} else "SHADOW"
        status = "BLOCKED_INSUFFICIENT_EVIDENCE" if insufficient_evidence else "SHADOW_NOT_PROMOTED"
        return PromotionTransition(previous, level, status, False, reasons)

    if previous in {"BLOCKED", "DEGRADED", "ROLLED_BACK"}:
        return PromotionTransition(previous, "SHADOW", "RECOVERED_TO_SHADOW", True, ())
    next_level = _NEXT.get(previous, "SHADOW")
    status = "FULL_RISK_PROMOTION" if next_level == "FULL_RISK_PROMOTION" else f"ADVANCED_TO_{next_level}"
    return PromotionTransition(previous, next_level, status, True, ())


def build_state_row(
    *,
    source_generation_id: str,
    transition: PromotionTransition,
    gate_results: Mapping[str, Any],
    artifact_checksum: str,
    evaluated_at: str,
) -> dict[str, Any]:
    payload = {
        "source_generation_id": source_generation_id,
        "previous_level": transition.previous_level,
        "promotion_level": transition.promotion_level,
        "promotion_status": transition.promotion_status,
        "all_gates_pass": transition.all_gates_pass,
        "blocking_reasons": list(transition.blocking_reasons),
        "gate_results": dict(gate_results),
        "artifact_checksum": artifact_checksum,
        "evaluated_at": evaluated_at,
        "calculation_version": VERSION,
    }
    payload["record_key"] = "PSTATE-" + stable_checksum(payload)[:24]
    return payload


__all__ = [
    "VERSION", "PROMOTION_STATES", "PromotionTransition", "stable_checksum",
    "latest_promotion_state", "transition_promotion_state", "build_state_row",
]
