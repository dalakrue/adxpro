"""Additive quality, lineage, incremental-refresh, and mobile evidence store.

The module reuses the existing canonical validators. It creates no prediction,
direction, reliability, or publication authority. Rows are staged by the Settings
transaction and inserted by ``services.canonical_snapshot_store`` in the same
SQLite transaction as the canonical generation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
import hashlib
import json
import math
import sqlite3
import time

import numpy as np
import pandas as pd

from services.canonical_snapshot_store import DB_PATH

VERSION = "history-quality-mobile-20260621-v1"
BUNDLE_KEY = "__history_quality_mobile_20260621__"
PAYLOAD_LIMIT_BYTES = 65536
SETTLED_VALUES = {"UNSETTLED", "PENDING", "SETTLED", "OBSERVED", "COMPLETED", "NOT_APPLICABLE", "SHADOW"}

COMMON_COLUMNS = """
  record_key TEXT PRIMARY KEY,
  calculation_id TEXT NOT NULL,
  calculation_generation INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  source TEXT NOT NULL,
  latest_completed_h1 TEXT NOT NULL,
  record_time TEXT,
  target_time TEXT,
  horizon INTEGER,
  data_signature TEXT,
  logic_version TEXT NOT NULL,
  settled_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  is_revision INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL
"""

SCHEMAS: dict[str, str] = {
    "source_freshness_history": COMMON_COLUMNS + "," + """
      source_identity TEXT NOT NULL, latest_source_timestamp TEXT,
      source_age_hours REAL, stale_threshold_hours REAL, stale_flag INTEGER NOT NULL,
      source_row_count INTEGER NOT NULL, rejection_reason TEXT
    """,
    "schema_drift_history": COMMON_COLUMNS + "," + """
      column_name TEXT NOT NULL, rule_id TEXT NOT NULL, expected_type TEXT,
      expected_range TEXT, expected_categories TEXT, observed_values TEXT,
      severity TEXT NOT NULL, blocking_flag INTEGER NOT NULL, baseline_reference TEXT
    """,
    "candle_integrity_history": COMMON_COLUMNS + "," + """
      issue_type TEXT NOT NULL, issue_count INTEGER NOT NULL, severity TEXT NOT NULL,
      blocking_flag INTEGER NOT NULL, rejected_rows INTEGER NOT NULL, detail TEXT
    """,
    "data_lint_history": COMMON_COLUMNS + "," + """
      rule_id TEXT NOT NULL, column_name TEXT, observed_value TEXT,
      threshold_value TEXT, status TEXT NOT NULL, severity TEXT NOT NULL,
      affected_rows INTEGER NOT NULL, detail TEXT
    """,
    "revision_lineage_history": COMMON_COLUMNS + "," + """
      candle_timestamp TEXT NOT NULL, field_name TEXT NOT NULL,
      original_value TEXT, revised_value TEXT, revision_source TEXT,
      revision_reason TEXT, detected_at TEXT NOT NULL,
      affected_generation INTEGER, full_rebuild_required INTEGER NOT NULL
    """,
    "cleaning_impact_history": COMMON_COLUMNS + "," + """
      cleaning_rule TEXT NOT NULL, evaluation_window TEXT NOT NULL,
      rows_changed INTEGER NOT NULL, accuracy_before REAL, accuracy_after REAL,
      coverage_before REAL, coverage_after REAL, forecast_mae_before REAL,
      forecast_mae_after REAL, reliability_before REAL, reliability_after REAL,
      cpu_cost_ms REAL, confidence REAL, status TEXT NOT NULL,
      promotion_decision TEXT NOT NULL
    """,
    "incremental_refresh_history": COMMON_COLUMNS + "," + """
      processing_stage TEXT NOT NULL, input_rows INTEGER NOT NULL,
      added_rows INTEGER NOT NULL, revised_rows INTEGER NOT NULL,
      reused_rows INTEGER NOT NULL, recomputed_rows INTEGER NOT NULL,
      duration_ms REAL, cpu_time_ms REAL, python_allocation_bytes INTEGER,
      rss_before_bytes INTEGER, rss_after_bytes INTEGER, cache_hit INTEGER NOT NULL,
      full_rebuild_reason TEXT
    """,
    "mobile_render_budget_history": COMMON_COLUMNS + "," + """
      viewport_profile TEXT NOT NULL, field_name TEXT NOT NULL,
      displayed_rows INTEGER NOT NULL, chart_points INTEGER NOT NULL,
      chart_traces INTEGER NOT NULL, payload_bytes INTEGER NOT NULL,
      render_time_ms REAL, server_rss_bytes INTEGER, budget_status TEXT NOT NULL,
      failure_reason TEXT
    """,
    "approximate_preview_audit_history": COMMON_COLUMNS + "," + """
      query_name TEXT NOT NULL, exact_row_count INTEGER NOT NULL,
      sample_size INTEGER NOT NULL, approximation_method TEXT NOT NULL,
      confidence_level REAL, error_bound REAL, response_time_ms REAL,
      exact_export_available INTEGER NOT NULL, canonical_use_prohibited INTEGER NOT NULL
    """,
}

INDEXES = {
    "source_freshness_history": "calculation_id,source_identity",
    "schema_drift_history": "calculation_id,column_name,rule_id",
    "candle_integrity_history": "calculation_id,issue_type",
    "data_lint_history": "calculation_id,rule_id,column_name",
    "revision_lineage_history": "candle_timestamp,field_name,detected_at",
    "cleaning_impact_history": "cleaning_rule,evaluation_window,created_at",
    "incremental_refresh_history": "calculation_id,processing_stage",
    "mobile_render_budget_history": "calculation_id,viewport_profile,field_name,created_at",
    "approximate_preview_audit_history": "calculation_id,query_name,created_at",
}

CATALOG = {
    "source_freshness_history": ("SYSTEM", "DATA_QUALITY", "one source per canonical generation", "calculation_id + source"),
    "schema_drift_history": ("SYSTEM", "DATA_QUALITY", "one column/rule violation per generation", "calculation_id + column_name + rule_id"),
    "candle_integrity_history": ("SYSTEM", "DATA_QUALITY", "one integrity issue type per generation", "calculation_id + issue_type"),
    "data_lint_history": ("SYSTEM", "DATA_QUALITY", "one lightweight lint rule per generation", "calculation_id + rule_id + column_name"),
    "revision_lineage_history": ("SYSTEM", "LINEAGE", "one revised candle field", "candle_timestamp + field_name + detected_at"),
    "cleaning_impact_history": ("FIELD_6", "SHADOW_RESEARCH", "one proposed cleaning rule per chronological evaluation", "cleaning_rule + evaluation_window + calculation_id"),
    "incremental_refresh_history": ("SYSTEM", "PERFORMANCE", "one processing stage per canonical generation", "calculation_id + processing_stage"),
    "mobile_render_budget_history": ("SYSTEM", "MOBILE", "one renderer invocation per device profile and generation", "calculation_id + viewport_profile + field_name + created_at"),
    "approximate_preview_audit_history": ("FIELD_6", "PREVIEW", "one approximate noncanonical preview query", "calculation_id + query_name + created_at"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _quote(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def ensure_quality_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS history_catalog(
      table_name TEXT PRIMARY KEY, field_name TEXT NOT NULL, workspace TEXT NOT NULL,
      grain TEXT NOT NULL, business_key TEXT NOT NULL, description TEXT NOT NULL,
      schema_version TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS history_watermarks(
      table_name TEXT PRIMARY KEY, latest_completed_h1 TEXT, last_calculation_id TEXT,
      last_generation INTEGER, data_signature TEXT, updated_at TEXT NOT NULL)""")
    for table, schema in SCHEMAS.items():
        conn.execute(f"CREATE TABLE IF NOT EXISTS {_quote(table)}({schema})")
        conn.execute(f"CREATE INDEX IF NOT EXISTS {_quote('idx_'+table+'_latest')} ON {_quote(table)}(latest_completed_h1 DESC,calculation_generation DESC)")
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_quote('uq_'+table+'_grain')} ON {_quote(table)}({INDEXES[table]})")
        field, workspace, grain, key = CATALOG[table]
        conn.execute(
            "INSERT OR REPLACE INTO history_catalog(table_name,field_name,workspace,grain,business_key,description,schema_version) VALUES(?,?,?,?,?,?,?)",
            (table, field, workspace, grain, key, f"{table.replace('_',' ')} evidence", VERSION),
        )


def _parse_utc(value: Any, *, nullable: bool = True) -> str | None:
    if value in (None, "") and nullable:
        return None
    ts = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(ts):
        raise ValueError(f"invalid UTC timestamp: {value}")
    return ts.isoformat()


def _normalise(table: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    if table not in SCHEMAS:
        raise KeyError(table)
    row = dict(raw)
    now = _utc_now()
    row.setdefault("created_at", now)
    row.setdefault("logic_version", VERSION)
    row.setdefault("settled_status", "NOT_APPLICABLE")
    row.setdefault("is_revision", 0)
    if str(row["settled_status"]).upper() not in SETTLED_VALUES:
        raise ValueError(f"unapproved settled_status: {row['settled_status']}")
    for name in ("latest_completed_h1", "record_time", "target_time", "created_at"):
        row[name] = _parse_utc(row.get(name), nullable=name in {"record_time", "target_time"})
    if str(row.get("symbol", "")).upper() != "EURUSD" or str(row.get("timeframe", "")).upper() != "H1":
        raise ValueError("quality histories are restricted to EURUSD/H1")
    latest = pd.Timestamp(row["latest_completed_h1"])
    if latest > pd.Timestamp.now(tz="UTC").floor("h"):
        raise ValueError("latest_completed_h1 is in the future")
    if row.get("record_time") and pd.Timestamp(row["record_time"]) > pd.Timestamp.now(tz="UTC"):
        raise ValueError("record_time is in the future")
    horizon = row.get("horizon")
    if row.get("target_time") and horizon is not None and row.get("record_time"):
        expected = pd.Timestamp(row["record_time"]) + pd.Timedelta(hours=int(horizon))
        if abs((pd.Timestamp(row["target_time"]) - expected).total_seconds()) > 60:
            raise ValueError("target_time does not match declared horizon")
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else row.get("payload_json")
    if isinstance(payload, str):
        try: payload = json.loads(payload)
        except Exception as exc: raise ValueError("payload_json is invalid") from exc
    payload = dict(payload or {})
    encoded = json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > PAYLOAD_LIMIT_BYTES:
        raise ValueError("payload_json exceeds bounded size")
    row["payload_json"] = encoded
    row["calculation_generation"] = int(row.get("calculation_generation") or 0)
    if row["calculation_generation"] < 1:
        raise ValueError("calculation_generation must be positive")
    row["is_revision"] = 1 if bool(row.get("is_revision")) else 0
    for flag in ("stale_flag", "blocking_flag", "full_rebuild_required", "cache_hit", "exact_export_available", "canonical_use_prohibited"):
        if flag in row and row[flag] is not None: row[flag] = 1 if bool(row[flag]) else 0
    if not row.get("record_key"):
        row["record_key"] = _hash([table, row.get("calculation_id"), {k: row.get(k) for k in sorted(row) if k != "payload_json"}])
    return row


def insert_quality_bundle(conn: sqlite3.Connection, bundle: Mapping[str, Iterable[Mapping[str, Any]]]) -> dict[str, Any]:
    ensure_quality_schema(conn)
    result: dict[str, Any] = {}
    for table, rows in bundle.items():
        if table not in SCHEMAS: continue
        allowed = {str(r[1]) for r in conn.execute(f"PRAGMA table_info({_quote(table)})")}
        inserted = ignored = 0
        latest = None
        for raw in rows or []:
            row = _normalise(table, raw)
            selected = [k for k in row if k in allowed]
            sql = f"INSERT OR IGNORE INTO {_quote(table)}({','.join(_quote(k) for k in selected)}) VALUES({','.join('?' for _ in selected)})"
            before = conn.total_changes
            conn.execute(sql, [row[k] for k in selected])
            if conn.total_changes > before: inserted += 1
            else: ignored += 1
            latest = row
        if latest:
            conn.execute(
                "INSERT OR REPLACE INTO history_watermarks(table_name,latest_completed_h1,last_calculation_id,last_generation,data_signature,updated_at) VALUES(?,?,?,?,?,?)",
                (table, latest["latest_completed_h1"], latest["calculation_id"], latest["calculation_generation"], latest.get("data_signature"), latest["created_at"]),
            )
        result[table] = {"inserted": inserted, "idempotent_ignored": ignored}
    return result


def _identity(canonical: Mapping[str, Any]) -> dict[str, Any]:
    latest = canonical.get("latest_completed_candle_time") or (canonical.get("market") or {}).get("latest_completed_candle_time")
    return {
        "calculation_id": str(canonical.get("canonical_calculation_id") or canonical.get("run_id") or ""),
        "calculation_generation": int(canonical.get("calculation_generation") or 0),
        "run_id": str(canonical.get("run_id") or canonical.get("canonical_calculation_id") or ""),
        "symbol": str(canonical.get("symbol") or "EURUSD").upper(),
        "timeframe": str(canonical.get("timeframe") or "H1").upper(),
        "source": str(canonical.get("source") or "UNKNOWN"),
        "latest_completed_h1": _parse_utc(latest, nullable=False),
        "record_time": _parse_utc(latest, nullable=False),
        "target_time": None,
        "horizon": None,
        "data_signature": str(canonical.get("data_signature") or ""),
        "logic_version": VERSION,
        "settled_status": "NOT_APPLICABLE",
        "created_at": _utc_now(),
        "is_revision": 0,
    }


def _frame_parts(frame: pd.DataFrame) -> tuple[pd.Series, dict[str, pd.Series], str | None]:
    aliases = {"open": ("open","o"), "high": ("high","h"), "low": ("low","l"), "close": ("close","c"), "volume": ("volume","tick_volume","real_volume")}
    lowered = {str(c).lower(): c for c in frame.columns}
    cols = {k: next((lowered[a] for a in names if a in lowered), None) for k,names in aliases.items()}
    time_col = next((c for c in frame.columns if str(c).lower() in {"time","timestamp","datetime","date"}), None)
    times = pd.to_datetime(frame[time_col] if time_col else frame.index, errors="coerce", utc=True)
    values = {k: pd.to_numeric(frame[c], errors="coerce") for k,c in cols.items() if c is not None}
    return times, values, str(time_col) if time_col is not None else None


def validate_post_calculation_contract(canonical: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    identity = _identity(canonical)
    if not identity["calculation_id"] or identity["calculation_generation"] < 1:
        errors.append("canonical identity is incomplete")
    reverse = canonical.get("reverse_10_current")
    if isinstance(reverse, Mapping): count = len(reverse)
    elif isinstance(reverse, (list, tuple)): count = len(reverse)
    else: count = 0
    if count != 10:
        errors.append(f"protected decision count is {count}, expected 10")
    for name in ("full_metric_snapshot", "final_decision", "regime", "reliability"):
        part = canonical.get(name)
        if isinstance(part, Mapping):
            for field in ("run_id", "calculation_generation", "data_signature"):
                got = part.get(field)
                if got not in (None, "") and str(got) != str(identity.get(field if field != "calculation_generation" else "calculation_generation")):
                    errors.append(f"{name}.{field} mixes canonical generations")
    return errors


def build_quality_history_bundle(
    frame: pd.DataFrame,
    canonical: Mapping[str, Any],
    *,
    validation_report: Any = None,
    elapsed_ms: float | None = None,
    cpu_time_ms: float | None = None,
    rss_before_bytes: int | None = None,
    rss_after_bytes: int | None = None,
    previous_row_count: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create bounded evidence from already-computed data and canonical outputs."""
    if not isinstance(frame, pd.DataFrame): frame = pd.DataFrame()
    base = _identity(canonical)
    contract_errors = validate_post_calculation_contract(canonical)
    times, values, time_col = _frame_parts(frame)
    now = pd.Timestamp.now(tz="UTC")
    latest_source = times.max() if times.notna().any() else None
    age = (now - latest_source).total_seconds()/3600.0 if latest_source is not None else math.inf
    report = validation_report.as_dict() if hasattr(validation_report, "as_dict") else dict(validation_report or {})
    critical = int(report.get("critical_failure_count") or 0)
    rejection = "; ".join(str(x.get("constraint_name") or x) for x in report.get("failed_constraints", [])[:8]) or None
    bundle: dict[str, list[dict[str, Any]]] = {name: [] for name in SCHEMAS}

    source_row = {**base, "source_identity": f"{base['symbol']}:{base['timeframe']}:{base['source']}", "latest_source_timestamp": latest_source.isoformat() if latest_source is not None else None, "source_age_hours": None if not math.isfinite(age) else age, "stale_threshold_hours": 8.0, "stale_flag": age > 8.0, "source_row_count": len(frame), "rejection_reason": rejection, "payload": {"validation_status": report.get("status"), "critical_failures": critical}}
    bundle["source_freshness_history"].append(source_row)

    required = {"time": time_col, **{k: k in values for k in ("open","high","low","close")}}
    for name, present in required.items():
        ok = bool(present)
        if not ok:
            bundle["schema_drift_history"].append({**base, "column_name": name, "rule_id": "REQUIRED_COLUMN", "expected_type": "UTC timestamp" if name=="time" else "numeric", "expected_range": None, "expected_categories": None, "observed_values": "MISSING", "severity": "CRITICAL", "blocking_flag": True, "baseline_reference": "EURUSD_H1_OHLC_V1", "payload": {}})
    if contract_errors:
        for i, message in enumerate(contract_errors):
            bundle["schema_drift_history"].append({**base, "column_name": "canonical_payload", "rule_id": f"POST_CALC_CONTRACT_{i+1}", "expected_type": "single-generation canonical contract", "expected_range": None, "expected_categories": None, "observed_values": message, "severity": "CRITICAL", "blocking_flag": True, "baseline_reference": "canonical-runtime-20260617", "payload": {}})

    duplicate_count = int(times.duplicated(keep=False).sum()) if len(times) else 0
    invalid_time = int(times.isna().sum()) if len(times) else 0
    future = int((times >= now.floor("h")).sum()) if len(times) else 0
    sorted_times = times.dropna().sort_values(kind="mergesort")
    gaps = sorted_times.diff().dt.total_seconds().div(3600.0)
    weekday = sorted_times.dt.weekday.le(4) & sorted_times.shift(1).dt.weekday.le(4)
    missing = int(np.maximum(0, np.floor(gaps.where(gaps.gt(1.01)&gaps.lt(48)&weekday, 1)-1)).sum()) if len(sorted_times) else 0
    o=values.get("open", pd.Series(dtype=float)); h=values.get("high", pd.Series(dtype=float)); l=values.get("low", pd.Series(dtype=float)); c=values.get("close", pd.Series(dtype=float))
    invalid_ohlc = int((~((l<=o)&(o<=h)&(l<=c)&(c<=h)&(h>=l))).sum()) if all(len(x)==len(frame) for x in (o,h,l,c)) and len(frame) else len(frame)
    weekend = int(times.dt.weekday.ge(5).sum()) if len(times) else 0
    issue_counts = {
        "DUPLICATE_TIMESTAMPS": duplicate_count, "MISSING_H1_INTERVALS": missing,
        "INVALID_OHLC_RELATIONSHIPS": invalid_ohlc, "FUTURE_CANDLES": future,
        "INCOMPLETE_CANDLES": future, "WEEKEND_ANOMALIES": weekend,
        "TIMEZONE_PROBLEMS": invalid_time, "REJECTED_ROWS": int(report.get("source_row_count",len(frame)) or len(frame))-int(report.get("cleaned_row_count",len(frame)) or len(frame)),
    }
    critical_types = {"DUPLICATE_TIMESTAMPS","INVALID_OHLC_RELATIONSHIPS","FUTURE_CANDLES","INCOMPLETE_CANDLES","TIMEZONE_PROBLEMS"}
    for issue, count in issue_counts.items():
        bundle["candle_integrity_history"].append({**base, "issue_type": issue, "issue_count": max(0,int(count)), "severity": "CRITICAL" if issue in critical_types else "WARNING", "blocking_flag": issue in critical_types and count>0, "rejected_rows": max(0,int(count)), "detail": "Single-pass completed-H1 integrity aggregate.", "payload": {}})

    numeric = frame.select_dtypes(include=[np.number])
    lint_rows: list[tuple[str,str|None,Any,Any,str,int,str]] = []
    for column in numeric.columns:
        s = pd.to_numeric(numeric[column], errors="coerce")
        unique = int(s.nunique(dropna=True)); missing_n=int(s.isna().sum())
        if unique <= 1: lint_rows.append(("CONSTANT_COLUMN",str(column),unique,">1","WARNING",len(s),"Column is constant."))
        elif unique/max(1,len(s)) < .01: lint_rows.append(("NEAR_CONSTANT_COLUMN",str(column),unique/max(1,len(s)),">=0.01","INFO",len(s)-unique,"Low uniqueness ratio."))
        if missing_n/max(1,len(s)) > .2: lint_rows.append(("EXCESSIVE_MISSINGNESS",str(column),missing_n/max(1,len(s)),"<=0.20","WARNING",missing_n,"Missingness exceeds threshold."))
    if "volume" in values and len(values["volume"]):
        zero_spikes=int((values["volume"]<=0).sum()); lint_rows.append(("ZERO_VOLUME_SPIKES","volume",zero_spikes,0,"WARNING" if zero_spikes else "INFO",zero_spikes,"Zero/nonpositive volume observations."))
    # Copied columns use hashes without materializing pairwise DataFrame copies.
    hashes: dict[str,str] = {}
    for column in numeric.columns[:40]:
        arr=pd.util.hash_pandas_object(numeric[column], index=False).values.tobytes(); digest=hashlib.sha1(arr).hexdigest()
        if digest in hashes: lint_rows.append(("COPIED_COLUMN",str(column),hashes[digest],"distinct","WARNING",len(frame),"Column duplicates another numeric column."))
        else: hashes[digest]=str(column)
    if not lint_rows: lint_rows.append(("LIGHTWEIGHT_LINT_SUMMARY",None,"no violations","no violations","INFO",0,"Bounded lint rules completed."))
    for rule,col,obs,thr,sev,affected,detail in lint_rows:
        bundle["data_lint_history"].append({**base, "rule_id":rule,"column_name":col,"observed_value":str(obs),"threshold_value":str(thr),"status":"PASS" if affected==0 else "CHECK","severity":sev,"affected_rows":int(affected),"detail":detail,"payload":{}})

    prior = max(0, int(previous_row_count or 0)); current=len(frame)
    added=max(0,current-prior); reused=min(prior,current); full_reason=None
    if canonical.get("metadata",{}).get("source_changed"): full_reason="SOURCE_CHANGE"
    elif canonical.get("metadata",{}).get("schema_changed"): full_reason="SCHEMA_CHANGE"
    elif canonical.get("metadata",{}).get("historical_revision"): full_reason="HISTORICAL_REVISION"
    bundle["incremental_refresh_history"].append({**base,"processing_stage":"CANONICAL_PUBLICATION","input_rows":current,"added_rows":added,"revised_rows":0,"reused_rows":reused,"recomputed_rows":current if full_reason or prior==0 else added,"duration_ms":elapsed_ms,"cpu_time_ms":cpu_time_ms,"python_allocation_bytes":None,"rss_before_bytes":rss_before_bytes,"rss_after_bytes":rss_after_bytes,"cache_hit":bool(prior and added==0 and not full_reason),"full_rebuild_reason":full_reason,"payload":{"contract_errors":contract_errors}})

    # Empty SHADOW/lineage/preview tables are deliberately not populated without evidence.
    compact = {k:v for k,v in bundle.items() if v}
    blocking = critical + sum(1 for row in bundle["schema_drift_history"] if row.get("blocking_flag")) + sum(1 for row in bundle["candle_integrity_history"] if row.get("blocking_flag"))
    summary = {"version":VERSION,"tables_staged":sorted(compact),"rows_staged":sum(len(v) for v in compact.values()),"blocking_failure_count":int(blocking),"post_contract_errors":contract_errors}
    return {BUNDLE_KEY: compact}, summary


def append_mobile_render_budget(row: Mapping[str, Any], *, db_path: Path | str = DB_PATH) -> dict[str, Any]:
    conn=sqlite3.connect(str(db_path),timeout=30,check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL"); conn.execute("BEGIN IMMEDIATE")
        result=insert_quality_bundle(conn,{"mobile_render_budget_history":[row]}); conn.commit(); return result
    except Exception: conn.rollback(); raise
    finally: conn.close()


__all__ = ["VERSION","BUNDLE_KEY","SCHEMAS","ensure_quality_schema","insert_quality_bundle","validate_post_calculation_contract","build_quality_history_bundle","append_mobile_render_budget"]
