"""Compact evidence registry over the latest completed canonical generation."""
from __future__ import annotations
from hashlib import sha1
from typing import Any, Mapping, MutableMapping, Iterable


def _m(v: Any) -> Mapping[str, Any]:
    return v if isinstance(v, Mapping) else {}


def _nonempty(v: Any) -> bool:
    return v not in (None, "", [], {})


def _record(source: str, field: str, metric: str, value: Any, explanation: str, *, generation_id: str, completed: Any, symbol: str, timeframe: str, reliability: Any = None, freshness: str = "CURRENT", evidence_status: str = "SETTLED") -> dict[str, Any]:
    raw = f"{generation_id}|{source}|{field}|{metric}|{value}"
    return {
        "evidence_id": sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16],
        "source_name": source,
        "generation_id": generation_id,
        "completed_candle": completed,
        "symbol": symbol,
        "timeframe": timeframe,
        "field": field,
        "metric_name": metric,
        "metric_value": value,
        "short_explanation": explanation,
        "reliability": reliability,
        "freshness": freshness,
        "evidence_status": evidence_status,
    }


def build_source_registry(canonical: Mapping[str, Any], summary: Mapping[str, Any], plan: Mapping[str, Any] | None = None, extra_records: Iterable[Mapping[str, Any]] | None = None, *, max_records: int = 80) -> list[dict[str, Any]]:
    plan = _m(plan)
    identity = _m(summary.get("identity"))
    generation_id = str(summary.get("calculation_id") or canonical.get("canonical_calculation_id") or canonical.get("run_id") or "")
    completed = identity.get("latest_completed_candle_time") or canonical.get("latest_completed_candle_time")
    symbol = str(identity.get("symbol") or canonical.get("symbol") or "EURUSD")
    timeframe = str(identity.get("timeframe") or canonical.get("timeframe") or "H1")
    validation = _m(summary.get("validation"))
    freshness = str(validation.get("stale_status") or validation.get("data_freshness") or "UNKNOWN")
    regime_rel = _m(summary.get("regime")).get("regime_reliability")
    records: list[dict[str, Any]] = []

    def add(source: str, field: str, metric: str, value: Any, explanation: str, reliability: Any = None, status: str = "SETTLED") -> None:
        if _nonempty(value) and len(records) < max_records:
            records.append(_record(source, field, metric, value, explanation, generation_id=generation_id, completed=completed, symbol=symbol, timeframe=timeframe, reliability=reliability, freshness=freshness, evidence_status=status))

    add("Canonical identity", "system_health", "generation_id", generation_id, "Published canonical generation identity.", 100)
    add("Canonical identity", "system_health", "completed_candle", completed, "Latest completed H1 candle used by the generation.", 100)
    add("Canonical market", "decision", "current_price", _m(summary.get("projection")).get("current_close"), "Current close from the completed generation.", 100)

    for key, value in _m(summary.get("decision")).items():
        add("Canonical final decision", "decision", key, value, "Protected final-decision output.", regime_rel)
    for key, value in _m(summary.get("scores")).items():
        add("Protected Full Metric scores", "scores", key, value, "Protected score copied without recalculation.", regime_rel)
    for key, value in _m(summary.get("regime")).items():
        add("Canonical regime", "regime", key, value, "Published regime and transition output.", regime_rel)
    for key, value in _m(summary.get("projection")).items():
        add("Published Power BI projection", "projection", key, value, "Cached path/interval output from the completed generation.", _m(summary.get("projection")).get("projection_confidence"))
    for key, value in _m(summary.get("priority")).items():
        if key != "top_two":
            add("Canonical priority", "priority", key, value, "Published KNN/Greedy priority output.", regime_rel)
    for key, value in _m(summary.get("uncertainty")).items():
        add("Calibration and uncertainty", "reliability", key, value, "Published uncertainty/calibration evidence.", regime_rel)
    for key, value in validation.items():
        add("Validation", "system_health", key, value, "Published validation and freshness status.", 100)
    for key, value in _m(summary.get("similar_day")).items():
        add("Similar-Day intelligence", "similar_day", key, value, "Published historical analogue summary.", _m(summary.get("similar_day")).get("reliability"))
    for key, value in _m(summary.get("nlp")).items():
        add("Published NLP summary", "evidence", key, value, "Settled local/news evidence summary.", _m(summary.get("nlp")).get("reliability"))

    risk_map = {
        "status": plan.get("status"), "recommended_lots": plan.get("recommended_lots"),
        "planned_risk_pct": plan.get("planned_risk_pct"), "planned_dollar_loss": plan.get("planned_dollar_loss"),
        "margin_estimate": plan.get("margin_estimate"), "reason": plan.get("reason"),
        "stop_loss_pips": _m(plan.get("inputs")).get("stop_loss_pips"),
    }
    for key, value in risk_map.items():
        add("Published position sizing", "risk", key, value, "Read-only published risk/position-sizing output.", regime_rel)

    for raw in list(extra_records or [])[:16]:
        if not isinstance(raw, Mapping):
            continue
        metric = raw.get("metric_name") or raw.get("condition") or "settled_evidence"
        value = raw.get("value_text") if _nonempty(raw.get("value_text")) else raw.get("value_numeric")
        add(str(raw.get("source_name") or raw.get("table_name") or "Settled evidence"), str(raw.get("field") or "evidence"), str(metric), value, str(raw.get("short_explanation") or "Settled evidence record."), raw.get("reliability"), str(raw.get("settled_status") or "SETTLED"))
    return records[:max_records]


def load_settled_evidence(required_sources: Iterable[str], *, max_tables: int = 4, rows_per_table: int = 4) -> list[dict[str, Any]]:
    """Load only a tiny selected settled-evidence sample after the user submits."""
    try:
        from core.history_evidence_store_20260620 import catalog_frame, query_history
        catalog = catalog_frame()
    except Exception:
        return []
    if getattr(catalog, "empty", True):
        return []
    wanted = {str(x).lower() for x in required_sources}
    selected: list[str] = []
    for row in catalog.to_dict("records"):
        table = str(row.get("table_name") or row.get("name") or "")
        field = str(row.get("field") or row.get("field_name") or "")
        hay = f"{table} {field}".lower()
        if not wanted or any(token in hay for token in wanted):
            selected.append(table)
        if len(selected) >= max_tables:
            break
    output: list[dict[str, Any]] = []
    for table in selected:
        try:
            frame = query_history(table, limit=rows_per_table)
        except Exception:
            continue
        if getattr(frame, "empty", True):
            continue
        compact_cols = [c for c in ("latest_completed_h1", "record_time", "condition", "metric_name", "value_numeric", "value_text", "coverage_flag", "settled_status", "calculation_generation") if c in frame.columns]
        for row in frame.loc[:, compact_cols].to_dict("records"):
            row["table_name"] = table
            output.append(row)
    return output[: max_tables * rows_per_table]

__all__ = ["build_source_registry", "load_settled_evidence"]
