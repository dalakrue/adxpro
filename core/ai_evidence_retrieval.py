"""Bounded lexical/metadata evidence retrieval without a heavy embedding model."""
from __future__ import annotations
import re
from typing import Any, Iterable, Mapping


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9+_.%-]+", str(value or "").lower()))


def retrieve_evidence(question: str, registry: Iterable[Mapping[str, Any]], required_sources: Iterable[str], *, top_k: int = 6) -> list[dict[str, Any]]:
    q = _tokens(question)
    required = {str(x).lower() for x in required_sources}
    scored: list[tuple[float, dict[str, Any]]] = []
    for raw in registry:
        rec = dict(raw)
        text = " ".join(str(rec.get(k, "")) for k in ("source_name", "field", "metric_name", "metric_value", "short_explanation", "evidence_status"))
        terms = _tokens(text)
        overlap = len(q & terms)
        field = str(rec.get("field", "")).lower()
        source_bonus = 3.0 if field in required or any(token in text.lower() for token in required) else 0.0
        settled_bonus = 1.0 if str(rec.get("evidence_status", "")).upper() in {"SETTLED", "OBSERVED", "COMPLETED"} else 0.0
        freshness_bonus = 1.0 if str(rec.get("freshness", "")).upper() in {"CURRENT", "FRESH", "READY"} else 0.0
        reliability = rec.get("reliability")
        try:
            reliability_bonus = min(max(float(reliability), 0.0), 100.0) / 100.0
        except Exception:
            reliability_bonus = 0.0
        score = overlap * 2.0 + source_bonus + settled_bonus + freshness_bonus + reliability_bonus
        if score > 0:
            rec["retrieval_score"] = round(score, 3)
            scored.append((score, rec))
    ranked = [r for _, r in sorted(scored, key=lambda x: (-x[0], str(x[1].get("metric_name"))))[: max(1, min(int(top_k), 8))]]
    # Lost-in-the-Middle mitigation: strongest evidence at the beginning, second
    # strongest at the end, with the remainder in descending order between them.
    if len(ranked) > 2:
        ranked = [ranked[0], *ranked[2:], ranked[1]]
    return ranked

__all__ = ["retrieve_evidence"]
