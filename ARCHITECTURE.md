# Architecture

## Runtime contract

- Entrypoint: `app.py`
- Runtime: Python 3.12 (`runtime.txt`)
- Framework: Streamlit
- Canonical computation trigger: the existing **Run Calculation** action in Settings
- Canonical publication: one atomic publication with one `run_id` and one `calculation_generation`
- Display rule: Lunch, Dinner/Regime, Finder, visualization, NLP, priority, conflict, and trust views read the published canonical generation; display interaction does not execute the calculator.

## Protected calculation path

1. API/data validation and existing preprocessing run through `core/settings_run_orchestrator_20260617.py`.
2. Existing formulas, models, regime engine, priorities, conflicts, Similar-Day engine, and decision product are produced unchanged.
3. `build_regime_transition_trust(...)` receives the completed H1 data and already-produced canonical outputs.
4. It creates an **EVIDENCE_ONLY** payload and normalized history rows. It deep-copies the canonical result and only adds `regime_transition_trust_center` plus metadata.
5. Existing pre-publication validation runs.
6. `publish_canonical_atomically(...)` saves the complete canonical generation once.
7. The DuckDB trust sidecar receives incremental rows after successful publication. A sidecar failure is noncritical and cannot invalidate the canonical result.
8. Operational synchronization republishes aliases from the same canonical object/generation.
9. Router state changes to Lunch, opens Field 1, sets a focus/scroll flag, and displays the completed result without a second calculation.

## UI placement

### Lunch

The authoritative renderer has exactly four principal open/close fields. Search appears immediately after Quick Decision and before Field 1. Field 4 remains exactly:

`4. Similar-Day Intelligence + All Current Data`

Field 4 order:

1. Similar-Day Intelligence summary
2. Summary cards
3. Top-five similar results
4. Complete descending 25-day history
5. Similarity explanation and reliability warning
6. Existing All Current Data
7. Existing copy and export controls

The former additional workspace and AI functions remain available as nested cached views inside Field 4, avoiding extra principal Lunch fields.

### Dinner/Regime

`6. Regime Transition, Drift & System Trust Center` is an open/close field inside the existing Dinner/Regime area. It is not a top-level page, tab, sidebar item, or Lunch field.

## Storage

- Existing canonical SQLite transaction: remains authoritative for the trading generation.
- `data/regime_trust_history.duckdb`: analytical sidecar for normalized transition, outcome, calibration, drift, decision-audit, and component-error history.
- `data/history_parquet/`: periodic ZSTD Parquet checkpoints when the bounded persistence threshold is met.
- `st.cache_resource`: stable DuckDB store resource.
- `st.cache_data`: immutable transition-match display data keyed by run ID and generation.
- Queries use bounded row limits and column projection; large tables are rendered only behind explicit open/close gates.

## Failure containment

Optional trust, calibration, search, history matching, and chart failures show a plain-language message, write a safe internal error row where possible, and leave the last valid canonical result available. API keys are excluded from normalized history and redacted from searchable paths/log messages.

## Audit artifacts

- `FULL_PROJECT_INSPECTION_20260621.md`
- `FULL_PROJECT_INSPECTION_20260621.json`

The JSON contains per-file SHA-256, sizes, text/Python inspection, and database schema inventory.
