"""Lexical, deterministic intent detection for the read-only AI assistant."""
from __future__ import annotations
import re
from typing import Any

INTENTS = {
    "decision_explanation": ("decision", "buy", "sell", "wait", "entry", "why"),
    "regime_explanation": ("regime", "alpha", "delta", "transition", "trend"),
    "reliability_explanation": ("reliability", "confidence", "uncertainty", "calibration", "trust"),
    "powerbi_path": ("power bi", "powerbi", "forecast", "projection", "path", "band", "price"),
    "similar_day": ("similar day", "pattern", "historical match", "analogue"),
    "historical_comparison": ("history", "historical", "compare", "previous", "last 25"),
    "priority_ranking": ("priority", "rank", "knn", "greedy", "best hour", "opportunity"),
    "risk_position_sizing": ("risk", "position", "lot", "margin", "stop", "tp", "sl", "sizing"),
    "system_health": ("fresh", "stale", "health", "connector", "data", "generation", "ready", "status"),
}

SOURCE_MAP = {
    "decision_explanation": ("decision", "scores", "regime", "reliability", "warnings"),
    "regime_explanation": ("regime", "reliability", "history"),
    "reliability_explanation": ("reliability", "uncertainty", "validation", "evidence"),
    "powerbi_path": ("projection", "forecast", "reliability", "validation"),
    "similar_day": ("similar_day", "history", "reliability"),
    "historical_comparison": ("history", "decision", "regime", "evidence"),
    "priority_ranking": ("priority", "decision", "regime", "reliability"),
    "risk_position_sizing": ("risk", "decision", "scores", "warnings"),
    "system_health": ("identity", "validation", "connector", "evidence", "warnings"),
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+_-]+", str(text or "").lower()))


def detect_intent(question: str) -> dict[str, Any]:
    q = str(question or "").strip().lower()
    tokens = _tokens(q)
    scored: list[tuple[int, str]] = []
    for intent, phrases in INTENTS.items():
        score = 0
        for phrase in phrases:
            phrase_l = phrase.lower()
            if " " in phrase_l:
                score += 3 if phrase_l in q else 0
            elif phrase_l in tokens:
                score += 2
        scored.append((score, intent))
    score, intent = max(scored, default=(0, "decision_explanation"))
    if score <= 0:
        intent = "decision_explanation"
    return {
        "intent": intent,
        "score": score,
        "required_sources": SOURCE_MAP[intent],
        "normalized_question": " ".join(q.split()),
    }

__all__ = ["detect_intent", "INTENTS", "SOURCE_MAP"]
