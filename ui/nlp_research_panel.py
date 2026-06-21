"""Lightweight local NLP fallback; no external API and no model training."""
from __future__ import annotations
from typing import Any, Mapping

def run_nlp_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
    text = str(kwargs.get("text") or "")
    return {"status":"READY" if text else "NO_INPUT", "direction":"WAIT", "reliability":0.0, "conflict_level":"NONE", "latest_headline": text[:240] if text else "No relevant news", "external_api":False}
