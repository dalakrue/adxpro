# Database Migration Report — Ten-Paper Shadow Layers

## Migration artifacts

- SQL: `migrations/20260621_ten_paper_shadow_layers.sql`
- Utility: `tools/migrate_ten_paper_20260621.py`
- Store implementation: `core/research_validation_store_20260621.py`
- Schema version marker: `PRAGMA user_version = 20260621`

## New idempotent tables

1. `model_x_knockoff_feature_history`
2. `online_fdr_test_history`
3. `online_fdr_state`
4. `reject_option_history`
5. `flexible_loss_history`
6. `model_explanation_cache`
7. `monotonicity_validation_history`
8. `delta_maintenance_history`
9. `exact_delta_state`
10. `provenance_node`
11. `provenance_edge`
12. `metamorphic_test_history`
13. `calm_operation_classification`
14. `evidence_gate_history`
15. `research_paper_run`

Each table has a deterministic primary key and `payload_json` preserving the complete bounded row. Generation/time indexes support source-specific queries. Reapplying the migration is safe because all DDL uses `IF NOT EXISTS`.

## Atomic write behavior

Rows are staged under the existing `__research_validation_20260621__` bundle key. `services/canonical_snapshot_store.commit_snapshot` inserts them inside the canonical `BEGIN IMMEDIATE` transaction. There is no independent post-publication write path.

## Backup behavior

Run:

```powershell
py -3.12 tools\migrate_ten_paper_20260621.py --backup
```

The utility uses SQLite's backup API and creates a timestamped file beside the database before applying DDL. On migration exception, it restores the backup automatically when available.

## Rollback behavior

```powershell
py -3.12 tools\migrate_ten_paper_20260621.py --rollback "data\canonical_runtime.sqlite3.before_ten_paper_YYYYMMDDTHHMMSSZ.bak"
```

Before restoring, the utility creates a second safety copy of the current database and runs `PRAGMA quick_check` after restoration.

## Verification performed

- Migration applied twice to a temporary copy: PASS.
- Expected 15 tables found: PASS.
- `PRAGMA user_version`: 20260621.
- `PRAGMA quick_check`: PASS.
- Insert bundle replay: second replay inserted zero duplicate rows.
- Atomic rollback test: staged generation and research rows were absent after injected failure; previous completed generation remained current.

The shipped `data/canonical_runtime.sqlite3` was restored to its original bytes after testing. Users control when to apply the migration.
