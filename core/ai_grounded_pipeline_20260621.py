"""Ten-stage local grounded-answer pipeline over one completed generation."""
from __future__ import annotations
from typing import Any, Mapping, MutableMapping

from core.ai_intent_router import detect_intent
from core.ai_resource_budget import select_budget
from core.ai_source_registry import build_source_registry, load_settled_evidence
from core.ai_evidence_retrieval import retrieve_evidence
from core.ai_answer_planner import draft_answer, revise_answer, final_structured_answer
from core.ai_answer_critic import critique_answer
from core.ai_confidence_calibration import calibrate_confidence
from core.ai_conversation_memory import remember


def _m(v: Any) -> Mapping[str, Any]:
    return v if isinstance(v, Mapping) else {}


def answer_question(question: str, *, canonical: Mapping[str, Any], summary: Mapping[str, Any], plan: Mapping[str, Any] | None, state: MutableMapping[str, Any]) -> dict[str, Any]:
    # 1. Intent detection
    intent_info = detect_intent(question)
    intent = str(intent_info["intent"])
    required = tuple(intent_info["required_sources"])
    budget = select_budget(question, intent)

    identity_summary = _m(summary.get("identity"))
    generation_id = str(summary.get("calculation_id") or canonical.get("canonical_calculation_id") or canonical.get("run_id") or "")
    completed = identity_summary.get("latest_completed_candle_time") or canonical.get("latest_completed_candle_time")
    identity = {"generation_id": generation_id, "completed_candle": completed}

    # 2-3. Required-source selection and bounded settled-evidence retrieval
    settled = load_settled_evidence(required, max_tables=budget.max_history_tables, rows_per_table=3)
    registry = build_source_registry(canonical, summary, plan, settled, max_records=budget.max_registry_records)
    evidence = retrieve_evidence(question, registry, required, top_k=budget.top_k)

    # 4. Read-only calculation selection: select already-published values only.
    # 5. Freshness verification
    validation = _m(summary.get("validation"))
    stale = str(validation.get("stale_status") or "CURRENT").upper() == "STALE" or bool(state.get("dependent_calculations_stale_20260621"))
    freshness = "STALE_GENERATION" if stale else str(validation.get("data_freshness") or "CURRENT")

    # 6. Conflict verification
    decision = _m(summary.get("decision"))
    conflict_values = [str(decision.get("conflict_status") or ""), str(_m(summary.get("nlp")).get("conflict") or "")]
    conflict = any(x and x.upper() not in {"NONE", "NO", "LOW", "NO CONFLICT", "NO NLP DATA", "NOT AVAILABLE", "UNKNOWN", ""} for x in conflict_values)
    conflict_status = "CONFLICTING_EVIDENCE" if conflict else "NO MATERIAL CONFLICT DETECTED"

    # 7. Draft answer
    draft = draft_answer(question, intent, evidence, identity)
    # 8. Evidence critic
    critic = critique_answer(evidence, required_sources=required, stale=stale, conflict=conflict)
    # 9. One revision pass
    revised = revise_answer(draft, critic)
    # 10. Final structured answer
    calibration = calibrate_confidence(evidence, required_count=max(2, len(required)), stale=stale, conflict=conflict)
    limitations = [
        "Local lexical retrieval; no heavy language model or external AI API is used.",
        "Confidence is evidence-calibrated support, not a probability of market success.",
    ]
    final = final_structured_answer(revised, identity=identity, sources=evidence, critic=critic, calibration=calibration, freshness=freshness, conflict=conflict_status, limitations=limitations)
    if len(final) > budget.max_answer_chars:
        final = final[: budget.max_answer_chars - 80].rsplit("\n", 1)[0] + "\n[Answer compressed to local resource budget]"
    remember(state, question=question, intent=intent, generation_id=generation_id, evidence=evidence, status=str(critic.get("status")))
    return {
        "answer": final,
        "status": critic.get("status"),
        "intent": intent,
        "generation_id": generation_id,
        "completed_candle": completed,
        "evidence": evidence,
        "calibration": calibration,
        "freshness": freshness,
        "conflict": conflict_status,
        "stages": [
            "intent_detection", "required_source_selection", "evidence_retrieval", "read_only_calculation_selection",
            "freshness_verification", "conflict_verification", "draft_answer", "evidence_critic",
            "one_revision_pass", "final_structured_answer",
        ],
    }

__all__ = ["answer_question"]
