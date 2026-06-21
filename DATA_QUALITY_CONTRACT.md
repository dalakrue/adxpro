# Data Quality Contract

Generated: 2026-06-21T15:26:21.707161+00:00

## Authority
`core.canonical_data_validation_20260621.validate_source_frame` remains Level A preflight. `validate_canonical_payload` plus `core.canonical_runtime_20260617.validate_canonical_result` remain Level B publication gates. `services.canonical_snapshot_store.commit_snapshot` is the sole SQLite publication authority. New history code records evidence and adds cross-generation/ten-decision invariants; it does not calculate trading outputs.

## Common history identity
Every new table contains: `record_key`, `calculation_id`, `calculation_generation`, `run_id`, `symbol`, `timeframe`, `source`, `latest_completed_h1`, `record_time`, `target_time`, `horizon`, `data_signature`, `logic_version`, `settled_status`, `created_at`, `is_revision`, and bounded `payload_json`.

Rules enforced at insertion: EURUSD/H1 only; positive generation; approved settled statuses; parseable UTC timestamps; no future completed H1; horizon/target reconciliation; JSON validity; 64 KiB payload bound; unique declared grain; idempotent `INSERT OR IGNORE`; monotonic generation recorded by watermarks.

## Level A — before expensive calculation
Required time/OHLC schema, numeric/finite data, UTC normalization, unique and monotonic timestamps, completed H1, OHLC relations, nonnegative spread, row-count reconciliation, source identity, minimum/freshness evidence, and missing weekday H1 intervals. Critical failures return before protected calculation and preserve the last valid generation.

## Level B — after calculation, before publication
The canonical validator checks identity, generation, status, completed H1, Full Metric contract and research invariants. The additive post-contract checks exactly ten protected decisions and rejects explicit cross-generation identity conflicts. Canonical snapshot plus generic, research and quality histories commit under one `BEGIN IMMEDIATE`; an exception rolls back all staged rows.

## Cleaning and approximation
`cleaning_impact_history` and `approximate_preview_audit_history` are deliberately empty until real chronological evidence or an explicit preview exists. Cleaning cannot be promoted from module presence. Approximation is prohibited for canonical decisions, protected metrics, validation, settlements and exact exports.
