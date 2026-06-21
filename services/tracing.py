"""Compact tracing helper; stores scalar records, never full DataFrames."""
from __future__ import annotations
from typing import Any, MutableMapping


def record(state: MutableMapping[str, Any], **event: Any) -> None:
    compact = {str(k): v for k, v in event.items() if not hasattr(v, "columns")}
    rows = list(state.get("compact_trace_events_20260621") or [])
    rows.append(compact)
    state["compact_trace_events_20260621"] = rows[-80:]
