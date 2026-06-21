# EURUSD H1 Canonical Architecture Report — 2026-06-19

## Canonical paths

- **Streamlit entry:** `app.py`
- **Compatibility entry:** `adx_dashpoard.py` (thin call into the app shell)
- **Application shell:** `core/app_shell.py`
- **Canonical UI runner:** `core/app/runner.py::run_app`
- **Canonical calculation entry:** `core/settings_run_orchestrator_20260617.py::run_settings_calculation`
- **Protected shared calculation interface:** `core/adx_shared_sync_20260615.py`
- **Canonical publication:** `core/canonical_runtime_20260617.py::publish_canonical_atomically`
- **Immutable snapshot schema:** `core/snapshot_schema_20260619.py::RunSnapshot`
- **Cross-tab synchronization:** `core/operational_sync_20260618.py::synchronize_published_generation`
- **Metadata/snapshot database:** `data/canonical_runtime.sqlite3` (created at runtime)
- **Disk-backed analytical frame store:** `data/adx_runtime_store.sqlite3` (created at runtime)
- **Existing application database:** `data/quant_app.sqlite3` (role preserved)

## Transaction and publication flow

1. The existing protected calculations execute once through the Settings orchestrator.
2. Required outputs are validated.
3. The display-only position-sizing guardrail is calculated from the completed canonical result.
4. A checksumed, frozen `RunSnapshot` is built.
5. Snapshot metadata is written in one SQLite `BEGIN IMMEDIATE` transaction.
6. The run is marked `COMPLETED` only after the snapshot row succeeds.
7. Session-state canonical pointers are published only after the database commit.
8. Lunch, Finder, Dinner, Morning, Data Visualization, Priority, NLP, AI, Train Data, Backtest, Profile, Engine and Pre-original receive aliases for the same run ID and generation.
9. A failed calculation or failed snapshot commit leaves the prior completed generation intact.

## Information hiding

Active tabs do not calculate a second trading result. Finder is read-only and queries the disk-backed canonical priority table. Lunch consumes the compact canonical summary and display-only risk plan. Train Data renders metadata and a bounded preview without retraining.

## Storage roles

- **SQLite canonical runtime:** run identity, generation, status, checksum and compact snapshot JSON.
- **SQLite frame store:** bounded/paginated display access to large frames already produced by protected logic.
- **Existing `quant_app.sqlite3`:** existing project records; not replaced.
- **CSV:** retained for existing compatibility and explicit user exports; no new per-run duplicate CSV writer was added.
- **DuckDB/Parquet:** dependencies remain available for existing analytics; they are not introduced as a second source of trading truth.

## Legacy adapters retained

- `app.py`
- `adx_dashpoard.py`
- `core/app_shell.py`
- Existing tab modules and compatibility aliases required by current routes

They remain thin routing/compatibility layers. No protected calculation module was deleted.

## Duplicate systems disabled or consolidated

- Native sidebar rendering is disabled by default and retained only as an explicit fallback.
- Finder no longer owns a calculation path.
- Train Data opening does not retrain.
- The Other/inner-tab route no longer asks for a second calculation after a completed canonical run.
- Copy/export serialization is generated only after a user action and is identity-checked against the displayed generation.

## Performance design

- One compact canonical summary in session state.
- Immutable run identity and checksum.
- Lazy Finder query and database-level filters/pagination.
- Lazy copy/export JSON creation.
- Bounded history previews.
- Closed fields avoid heavy chart/table construction where existing toggles permit it.
- Optional heavy NLP/tuning packages are separated from normal deployment requirements.
- Lightweight run tracing records duration, RSS and CPU when `psutil` is available.
