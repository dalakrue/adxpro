# Full Project Inventory

Generated: 2026-06-21T15:26:21.707161+00:00

## Recovery boundary
The uploaded ZIP lacks a central directory and ends inside a local file entry. 317 entries were recoverable from the upload, while its embedded manifest declares 924 expected files. To produce a runnable best-effort tree, the public repository's initial commit was used as a base and the 317 newer recovered files were overlaid. The resulting tree currently has 751 files and 458 Python files. Of the manifest's 924 files, 632 are byte-identical, 62 differ, and 230 remain unavailable. This is not represented as a byte-complete copy of the uploaded latest release.

## Active runtime trace
`app.py` → `adx_dashpoard.py` → `core.app_shell.run_app` → `core.app.runner.run_app` → `core.app.routes.load_tab` → `tabs.antd_page_router_20260615`. Settings uses `core.settings_run_orchestrator_20260617.run_settings_calculation`; shared reads use `core.adx_shared_sync_20260615.ensure_shared_calculation_result(force=False)`; canonical publication calls `core.canonical_runtime_20260617.publish_canonical_atomically` once, which calls `services.canonical_snapshot_store.commit_snapshot`.

## Static counts
- Python files: 458
- Function definitions: 2719
- Class definitions: 45
- Import occurrences: 2220
- Renderer/show functions: 309
- Distinct session-state keys found statically: 379
- Streamlit cache decorators found: 10
- Static `SELECT *` occurrences across all recovered/legacy code: 6 (the new history browser uses explicit projections)
- SQL CREATE TABLE occurrences found statically: 46
- SQLite databases: 4
- Test files present after recovery/addition: 2

## Detailed inventories
- `artifacts/FULL_FILE_INVENTORY_20260621.csv`: every packaged file, size, SHA-256 and manifest status.
- `HISTORY_TABLE_CATALOG.csv`: grain, business key, packaged row count and evidence status.
- `artifacts/PYTHON_IMPORT_INVENTORY_20260621.csv`: import call sites.
- `artifacts/SESSION_STATE_KEY_INVENTORY_20260621.csv`: statically referenced keys.
- `artifacts/RENDERER_INVENTORY_20260621.csv`: renderer definitions.
- `artifacts/DATABASE_TABLE_COUNTS_20260621.json`: table counts and integrity.
- `RECOVERED_MISSING_FROM_TRUNCATED_UPLOAD.txt`: unavailable expected files.

## Databases
| database | size bytes | integrity | table count | populated tables |
|---|---|---|---|---|
| data/adx_runtime_store.sqlite3 | 118784 | ok | 3 | canonical_summary=12 |
| data/adx_similarity_store.sqlite3 | 28672 | ok | 2 |  |
| data/canonical_runtime.sqlite3 | 1273856 | ok | 78 | history_catalog=44, run_snapshots=9, runs=9 |
| data/quant_app.sqlite3 | 114688 | ok | 3 | app_events=177 |

## Dependencies and deployment
`runtime.txt` targets Python 3.12. `requirements.txt` retains Streamlit Cloud-compatible dependencies and keeps platform-specific MetaTrader5 optional. No external API or paid service was added.
