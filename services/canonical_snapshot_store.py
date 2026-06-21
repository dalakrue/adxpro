"""Atomic SQLite publication authority for immutable canonical snapshots.

This module owns persistence only. It never calculates a trading value. A snapshot
and every staged history row are committed in one ``BEGIN IMMEDIATE`` transaction;
any exception rolls the complete transaction back.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
import json
import os
import sqlite3

DB_PATH = Path(os.getenv("ADX_CANONICAL_DB_PATH", Path(__file__).resolve().parents[1] / "data" / "canonical_runtime.sqlite3"))


def _json_safe(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return str(type(value).__name__)
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, MappingProxyType):
        value = dict(value)
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, depth + 1) for v in value]
    if hasattr(value, "to_dict") and hasattr(value, "columns"):
        try:
            return value.to_dict("records")
        except Exception:
            return {"type": type(value).__name__, "shape": list(getattr(value, "shape", ())) }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs(
          run_id TEXT NOT NULL,
          generation INTEGER NOT NULL,
          symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL,
          completed_candle TEXT,
          created_at TEXT NOT NULL,
          status TEXT NOT NULL,
          schema_version TEXT NOT NULL,
          checksum TEXT NOT NULL,
          source TEXT NOT NULL DEFAULT 'canonical',
          PRIMARY KEY(run_id,generation)
        );
        CREATE TABLE IF NOT EXISTS run_snapshots(
          run_id TEXT NOT NULL,
          generation INTEGER NOT NULL,
          snapshot_json TEXT NOT NULL,
          checksum TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(run_id,generation)
        );
        CREATE INDEX IF NOT EXISTS idx_runs_latest ON runs(generation DESC,created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_snapshots_latest ON run_snapshots(generation DESC,created_at DESC);
        """
    )


def _insert_history_bundles(conn: sqlite3.Connection, history_bundle: Mapping[str, Any]) -> dict[str, Any]:
    bundle = dict(history_bundle or {})
    result: dict[str, Any] = {}

    # Common Lunch/system histories.
    generic = {k: v for k, v in bundle.items() if not str(k).startswith("__")}
    if generic:
        from core.history_evidence_store_20260620 import insert_history_bundle
        result["history_evidence"] = insert_history_bundle(conn, generic)

    # Existing research-validation tables.
    research = bundle.get("__research_validation_20260621__")
    if isinstance(research, Mapping) and research:
        from core.research_validation_store_20260621 import insert_research_validation_bundle
        result["research_validation"] = insert_research_validation_bundle(conn, research)

    # Additive quality/lineage/mobile tables requested for this release.
    quality = bundle.get("__history_quality_mobile_20260621__")
    if isinstance(quality, Mapping) and quality:
        from core.history_quality_store_20260621 import insert_quality_bundle
        result["history_quality_mobile"] = insert_quality_bundle(conn, quality)
    return result


def commit_snapshot(run_snapshot: Any, *, history_bundle: Mapping[str, Any] | None = None, db_path: Path | str = DB_PATH) -> dict[str, Any]:
    """Commit a snapshot and all affected histories exactly once.

    Repeating the same ``run_id + generation + checksum`` is idempotent. Reusing
    that business key with a different checksum fails closed.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_safe(run_snapshot)
    run_id = str(payload.get("run_id") or "")
    generation = int(payload.get("generation") or 0)
    checksum = str(payload.get("checksum") or "")
    created_at = str(payload.get("calculation_completed_at") or payload.get("created_at") or "")
    if not run_id or generation < 1 or not checksum:
        raise ValueError("snapshot identity is incomplete")

    conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("BEGIN IMMEDIATE")
        ensure_schema(conn)
        existing = conn.execute(
            "SELECT checksum FROM run_snapshots WHERE run_id=? AND generation=?",
            (run_id, generation),
        ).fetchone()
        if existing and str(existing[0]) != checksum:
            raise ValueError("idempotency conflict: canonical business key already has a different checksum")

        snapshot_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        before = conn.total_changes
        conn.execute(
            "INSERT OR IGNORE INTO runs(run_id,generation,symbol,timeframe,completed_candle,created_at,status,schema_version,checksum,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                run_id, generation, str(payload.get("symbol") or "EURUSD"),
                str(payload.get("timeframe") or "H1"), str(payload.get("completed_candle") or ""),
                created_at, str(payload.get("status") or "COMPLETED"),
                str(payload.get("schema_version") or ""), checksum, "canonical",
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO run_snapshots(run_id,generation,snapshot_json,checksum,created_at) VALUES(?,?,?,?,?)",
            (run_id, generation, snapshot_json, checksum, created_at),
        )
        snapshot_inserted = conn.total_changes > before
        history_result = _insert_history_bundles(conn, history_bundle or {})
        conn.commit()
        return {
            "ok": True,
            "run_id": run_id,
            "generation": generation,
            "snapshot_inserted": snapshot_inserted,
            "idempotent": not snapshot_inserted,
            "histories": history_result,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def load_latest_snapshot(*, db_path: Path | str = DB_PATH) -> dict[str, Any] | None:
    path = Path(db_path)
    if not path.exists():
        return None
    conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT snapshot_json FROM run_snapshots ORDER BY generation DESC,created_at DESC LIMIT 1"
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


__all__ = ["DB_PATH", "ensure_schema", "commit_snapshot", "load_latest_snapshot"]
