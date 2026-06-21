# Database and Schema Migration Report — 2026-06-20

## Target database

`data/quant_app.sqlite3`

## Idempotent migration

File: `migrations/20260620_advanced_reliability_shift_v2.sql`

### `advanced_reliability_shift_snapshots_v2`

One compact JSON research snapshot per canonical calculation ID.

Columns: `calculation_id` (PK), `calculation_generation`, `latest_completed_h1_time`, `data_hash`, `version`, `publication_status`, `payload_json`, `created_at`, `published_at`.

### `advanced_reliability_shift_vectors_v2`

One bounded vector per calculation ID and stream type, currently used for the compact path-signature vector.

Columns: `calculation_id`, `calculation_generation`, `stream_type`, `vector_time`, `score`, `vector_json`, `created_at`; composite primary key `(calculation_id, stream_type)`.

### Indexes

- `idx_advanced_shift_generation_v2`
- `idx_advanced_shift_vector_time_v2`

## Transaction behavior

1. Research result is inserted/replaced as `STAGED` before canonical publication.
2. Stale generation writes are rejected relative to the latest published generation.
3. Canonical publication validates identity and commits the canonical snapshot.
4. The matching research row is then marked `PUBLISHED`.
5. Renderers read only the canonical published payload; they do not query or calculate the research tables.
6. Vector retention is bounded to the newest 1,024 rows.

## Existing schemas preserved

No existing table or column was deleted, renamed, or altered. The other databases retain their existing canonical snapshot, compact runtime, AI, and Similar-Day schemas.

## Rollback SQL

```sql
DROP INDEX IF EXISTS idx_advanced_shift_generation_v2;
DROP INDEX IF EXISTS idx_advanced_shift_vector_time_v2;
DROP TABLE IF EXISTS advanced_reliability_shift_vectors_v2;
DROP TABLE IF EXISTS advanced_reliability_shift_snapshots_v2;
```

Dropping these tables is optional when rolling back code because older code ignores them.

## Integrity verification

All four bundled SQLite databases returned `ok` from `PRAGMA integrity_check` after the migration. Exact table lists and row counts are in `reports/DATABASE_INTEGRITY_20260620.json`. The new v2 tables are intentionally empty in the distributed package and populate only after a successful user Run Calculation/canonical publication.
