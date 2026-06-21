"""Small persistent connector state machine shared by API controls."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, MutableMapping

DISCONNECTED = "DISCONNECTED"
CONNECTING = "CONNECTING"
CONNECTED = "CONNECTED"
ERROR = "ERROR"
VALID_STATES = {DISCONNECTED, CONNECTING, CONNECTED, ERROR}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize(state: MutableMapping[str, Any], prefix: str) -> None:
    state.setdefault(f"{prefix}_state", DISCONNECTED)
    state.setdefault(f"{prefix}_message", "")
    state.setdefault(f"{prefix}_updated_at", "")
    state.setdefault(f"{prefix}_request_id", 0)


def begin(state: MutableMapping[str, Any], prefix: str) -> bool:
    initialize(state, prefix)
    if state.get(f"{prefix}_state") == CONNECTING:
        updated = state.get(f"{prefix}_updated_at")
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(str(updated))).total_seconds()
        except Exception:
            age = 0.0
        if age < 90.0:
            return False
        state[f"{prefix}_state"] = ERROR
        state[f"{prefix}_message"] = "A stale connection lock was cleared safely."
    state[f"{prefix}_state"] = CONNECTING
    state[f"{prefix}_message"] = "Connection validation started."
    state[f"{prefix}_updated_at"] = _now()
    state[f"{prefix}_request_id"] = int(state.get(f"{prefix}_request_id", 0) or 0) + 1
    return True


def succeed(state: MutableMapping[str, Any], prefix: str, message: str = "Connected.") -> None:
    initialize(state, prefix)
    state[f"{prefix}_state"] = CONNECTED
    state[f"{prefix}_message"] = str(message)[:300]
    state[f"{prefix}_updated_at"] = _now()


def fail(state: MutableMapping[str, Any], prefix: str, message: str = "Connection failed.") -> None:
    initialize(state, prefix)
    state[f"{prefix}_state"] = ERROR
    state[f"{prefix}_message"] = str(message).replace("\n", " ")[:300]
    state[f"{prefix}_updated_at"] = _now()


def disconnect(state: MutableMapping[str, Any], prefix: str, message: str = "Disconnected.") -> None:
    initialize(state, prefix)
    state[f"{prefix}_state"] = DISCONNECTED
    state[f"{prefix}_message"] = str(message)[:300]
    state[f"{prefix}_updated_at"] = _now()


def snapshot(state: MutableMapping[str, Any], prefix: str) -> dict[str, Any]:
    initialize(state, prefix)
    value = str(state.get(f"{prefix}_state") or DISCONNECTED).upper()
    if value not in VALID_STATES:
        value = ERROR
    return {
        "state": value,
        "message": str(state.get(f"{prefix}_message") or ""),
        "updated_at": str(state.get(f"{prefix}_updated_at") or ""),
        "request_id": int(state.get(f"{prefix}_request_id", 0) or 0),
    }


__all__ = [
    "DISCONNECTED", "CONNECTING", "CONNECTED", "ERROR", "VALID_STATES",
    "initialize", "begin", "succeed", "fail", "disconnect", "snapshot",
]
