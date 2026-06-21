from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import sqlite3

import pandas as pd
import pytest

from core.history_quality_store_20260621 import (
    BUNDLE_KEY, SCHEMAS, build_quality_history_bundle, ensure_quality_schema,
    insert_quality_bundle, validate_post_calculation_contract,
)
from core.snapshot_schema_20260619 import RunSnapshot
from services.canonical_snapshot_store import commit_snapshot, ensure_schema


def frame(rows: int = 120) -> pd.DataFrame:
    end = pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=1)
    ts = pd.date_range(end=end, periods=rows, freq="h")
    return pd.DataFrame({
        "time": ts,
        "open": [1.10 + i * 1e-5 for i in range(rows)],
        "high": [1.11 + i * 1e-5 for i in range(rows)],
        "low": [1.09 + i * 1e-5 for i in range(rows)],
        "close": [1.105 + i * 1e-5 for i in range(rows)],
        "volume": [100 + (i % 10) for i in range(rows)],
    })


def canonical(generation: int = 1) -> dict:
    latest = frame(2)["time"].iloc[-1].isoformat()
    return {
        "run_id": f"RUN-{generation}", "canonical_calculation_id": f"RUN-{generation}",
        "calculation_generation": generation, "symbol": "EURUSD", "timeframe": "H1",
        "source": "TEST", "latest_completed_candle_time": latest,
        "data_signature": f"SIG-{generation}",
        "reverse_10_current": [{"decision": i + 1} for i in range(10)],
        "full_metric_snapshot": {}, "final_decision": {}, "regime": {}, "reliability": {},
    }


def snapshot(generation: int = 1, checksum: str = "abc") -> RunSnapshot:
    now = pd.Timestamp.now(tz="UTC").isoformat()
    return RunSnapshot(
        run_id=f"RUN-{generation}", generation=generation, symbol="EURUSD", timeframe="H1",
        calculation_started_at=now, calculation_completed_at=now,
        completed_candle=(pd.Timestamp.now(tz="UTC").floor("h")-pd.Timedelta(hours=1)).isoformat(),
        status="COMPLETED", schema_version="test", checksum=checksum,
        metrics={}, full_metric_history=[], regime={}, prediction={}, reliability={},
        priority={}, finder={}, nlp={}, risk_plan={},
    )


def test_all_nine_tables_and_common_contract(tmp_path: Path):
    db = tmp_path / "x.sqlite3"
    con = sqlite3.connect(db)
    ensure_quality_schema(con)
    expected_common = {
        "record_key", "calculation_id", "calculation_generation", "run_id", "symbol",
        "timeframe", "source", "latest_completed_h1", "record_time", "target_time",
        "horizon", "data_signature", "logic_version", "settled_status", "created_at",
        "is_revision", "payload_json",
    }
    assert len(SCHEMAS) == 9
    for table in SCHEMAS:
        cols = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
        assert expected_common <= cols
    con.close()


def test_good_bundle_is_bounded_and_nonblocking():
    bundle, summary = build_quality_history_bundle(frame(), canonical())
    assert summary["blocking_failure_count"] == 0
    assert BUNDLE_KEY in bundle
    assert sum(len(v) for v in bundle[BUNDLE_KEY].values()) < 100
    assert not bundle[BUNDLE_KEY].get("cleaning_impact_history")
    assert not bundle[BUNDLE_KEY].get("approximate_preview_audit_history")


def test_duplicate_timestamp_blocks():
    df = frame()
    df.loc[1, "time"] = df.loc[0, "time"]
    _, summary = build_quality_history_bundle(df, canonical())
    assert summary["blocking_failure_count"] >= 1


def test_protected_decision_count_blocks():
    c = canonical(); c["reverse_10_current"] = c["reverse_10_current"][:9]
    errors = validate_post_calculation_contract(c)
    assert any("expected 10" in x for x in errors)


def test_quality_insert_is_idempotent(tmp_path: Path):
    db = tmp_path / "quality.sqlite3"
    bundle, _ = build_quality_history_bundle(frame(), canonical())
    con = sqlite3.connect(db)
    con.execute("BEGIN IMMEDIATE")
    first = insert_quality_bundle(con, bundle[BUNDLE_KEY]); con.commit()
    con.execute("BEGIN IMMEDIATE")
    second = insert_quality_bundle(con, bundle[BUNDLE_KEY]); con.commit()
    assert sum(v["inserted"] for v in first.values()) > 0
    assert sum(v["inserted"] for v in second.values()) == 0
    assert sum(v["idempotent_ignored"] for v in second.values()) > 0
    con.close()


def test_snapshot_and_quality_are_one_transaction(tmp_path: Path):
    db = tmp_path / "canonical.sqlite3"
    bundle, _ = build_quality_history_bundle(frame(), canonical())
    result = commit_snapshot(snapshot(), history_bundle=bundle, db_path=db)
    assert result["ok"]
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM run_snapshots").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM source_freshness_history").fetchone()[0] == 1
    con.close()


def test_snapshot_idempotency_and_checksum_conflict(tmp_path: Path):
    db = tmp_path / "canonical.sqlite3"
    first = commit_snapshot(snapshot(), db_path=db)
    second = commit_snapshot(snapshot(), db_path=db)
    assert first["snapshot_inserted"] is True
    assert second["idempotent"] is True
    with pytest.raises(ValueError, match="idempotency conflict"):
        commit_snapshot(snapshot(checksum="different"), db_path=db)


def test_critical_history_error_rolls_back_snapshot(tmp_path: Path):
    db = tmp_path / "canonical.sqlite3"
    c = canonical()
    bundle, _ = build_quality_history_bundle(frame(), c)
    bad = dict(bundle)
    quality = {k: list(v) for k, v in bad[BUNDLE_KEY].items()}
    quality["source_freshness_history"][0] = dict(quality["source_freshness_history"][0], symbol="GBPUSD")
    bad[BUNDLE_KEY] = quality
    with pytest.raises(ValueError, match="restricted to EURUSD/H1"):
        commit_snapshot(snapshot(), history_bundle=bad, db_path=db)
    con = sqlite3.connect(db)
    ensure_schema(con)
    assert con.execute("SELECT COUNT(*) FROM run_snapshots").fetchone()[0] == 0
    con.close()


def test_payload_size_is_bounded(tmp_path: Path):
    bundle, _ = build_quality_history_bundle(frame(), canonical())
    row = dict(bundle[BUNDLE_KEY]["source_freshness_history"][0])
    row["payload"] = {"x": "a" * 70000}
    con = sqlite3.connect(tmp_path / "x.sqlite3")
    with pytest.raises(ValueError, match="bounded size"):
        insert_quality_bundle(con, {"source_freshness_history": [row]})
    con.close()


def test_closed_lunch_fields_execute_no_renderer(monkeypatch):
    import ui.lunch_four_core_fields_20260619 as lunch
    class FakeSt:
        def __init__(self): self.session_state = {}
        def markdown(self,*a,**k): pass
        def info(self,*a,**k): pass
        def toggle(self,*a,**k): return False
    fake = FakeSt()
    monkeypatch.setattr(lunch, "st", fake)
    for name in ("_render_field1","_render_field2","_render_field3","_render_field4","_render_field5","_render_field6"):
        monkeypatch.setattr(lunch, name, lambda *a, **k: (_ for _ in ()).throw(AssertionError("closed field executed")))
    lunch.render_lunch_six_core_fields()


def test_field1_has_only_two_required_history_headings():
    text = Path("ui/lunch_four_core_fields_20260619.py").read_text()
    assert 'Overall Full Metric History — Last 25 Days' in text
    assert 'All 10 Decision Histories — Last 25 Days' in text
    field1 = text[text.index("def _render_field1"):text.index("def _render_field2")]
    assert field1.count('st.markdown("####') == 2


def test_lunch_renderer_has_no_calculation_import():
    text = Path("ui/lunch_four_core_fields_20260619.py").read_text()
    assert "run_settings_calculation" not in text
    assert "ensure_shared_calculation_result(force=True)" not in text


def test_orchestrator_has_one_canonical_publication_call():
    text = Path("core/settings_run_orchestrator_20260617.py").read_text()
    assert text.count("adapter = publish_canonical_atomically(") == 1


def test_migration_is_idempotent(tmp_path: Path):
    con = sqlite3.connect(tmp_path / "m.sqlite3")
    ensure_quality_schema(con); ensure_quality_schema(con)
    assert len([r for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in SCHEMAS]) == 9
    con.close()
