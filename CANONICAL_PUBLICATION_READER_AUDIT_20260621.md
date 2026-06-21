# Canonical Publication and Reader Audit — 2026-06-21

Runtime references were traced from the real `app.py → adx_dashpoard.py → core.app_shell → core.app.runner` chain. The companion CSV contains every direct Python occurrence of the canonical publisher, canonical reader, protected canonical session keys, shared-calculation caller, and shared-result session key in `core`, `ui`, `tabs`, `services`, and the two entry files.

## Sole publication path

- `core/settings_run_orchestrator_20260617.py` calls `core/canonical_runtime_20260617.py::publish_canonical_atomically` once after pre-publication validation.
- `publish_canonical_atomically` calls `services/canonical_snapshot_store.py::commit_snapshot`.
- `commit_snapshot` uses the existing atomic SQLite transaction and commits the canonical snapshot plus the history/evidence bundle.
- No new publisher was added. The Production Promotion Guard is a pre-publication evidence producer and has no direction/action publisher.

## Shared calculation

- `core/adx_shared_sync_20260615.py::ensure_shared_calculation_result` remains the canonical shared calculation entry.
- Settings invokes it with `force=True`; normal rendering invokes it with `force=False` and reads the committed generation.

## Inventory counts

- CANONICAL_READ: 29
- CANONICAL_READ_DEFINITION: 1
- CANONICAL_SESSION_KEY_READ_OR_PROTECTION: 32
- PUBLISH_CALL: 4
- PUBLISH_DEFINITION: 1
- SHARED_CALCULATION_CALL: 2
- SHARED_CALCULATION_DEFINITION: 1
- SHARED_RESULT_SESSION_READ: 1

## Full occurrence inventory

See `CANONICAL_PUBLICATION_READER_AUDIT_20260621.csv`. Each row includes category, file, line and exact source text. Session-key protection references are retained because they control refresh/navigation preservation even when they do not fetch the payload.
