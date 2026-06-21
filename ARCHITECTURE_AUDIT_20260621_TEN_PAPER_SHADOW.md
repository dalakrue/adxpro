# ADX Quant Pro EURUSD H1 — Architecture Audit

**Audit date:** 2026-06-21  
**Scope:** uploaded full ZIP, active Python entry path, canonical calculation/publication path, research/history persistence, Lunch 4A/4B placement, tests, deployment files, and compatibility adapters.

## Audit coverage and honesty boundary

The package was extracted and inventoried as a complete filesystem. Every active Python file was compiled and every collected automated test was executed after the changes. Deep semantic review focused on the active entry points, Settings calculation orchestrator, canonical runtime/publication transaction, protected Full Metric/priority/reliability paths, research-validation layer, history bundle, SQLite schemas, Lunch 4A/4B renderers, Cloud requirements, and startup path. Historical reports/assets were inventoried but were not each manually reread line by line; they were treated as archived evidence rather than active executable logic.

## Package inventory

- Original archive: `f8ee5ef2-7db1-49a5-bf77-2557f5dec1d7.zip`
- Original archive size: approximately 1.9 MB.
- Original package inventory: 789 files, 489 Python files, 29 test modules after this addition (28 before it).
- Preferred entry point: `app.py`.
- Compatibility entry points: `main.py`, `adx_dashpoard.py`.
- Runtime target: Python 3.12 on Streamlit Community Cloud.
- Canonical SQLite database: `data/canonical_runtime.sqlite3`.
- Protected database file was restored to its original pre-test bytes; schema changes are delivered as an idempotent migration rather than silently baking test state into the database.

## Active call path

```text
app.py
  -> adx_dashpoard.main()
    -> core.app_shell.run_app()
      -> existing Settings "Run Calculation + Open Lunch"
        -> core/settings_run_orchestrator_20260617.py
          -> protected calculations / Full Metric / regime / reliability / priority
          -> history_research_pipeline_20260620.build_history_research_transaction()
          -> research_validation_layer_20260621.build_research_validation_transaction()
          -> ten_paper_research_layers_20260621.build_ten_paper_research_transaction() [new, once]
          -> canonical_data_validation_20260621.validate_canonical_payload()
          -> canonical_runtime_20260617.publish_canonical_atomically()
            -> snapshot_schema_20260619.build_run_snapshot()
            -> services/canonical_snapshot_store.commit_snapshot()
              -> BEGIN IMMEDIATE
              -> canonical run + snapshot
              -> existing history bundle
              -> research-validation + ten-paper rows
              -> mark COMPLETED
              -> COMMIT
```

## Canonical publication and read model

The authoritative result remains the existing canonical generation. The new transaction is attached as `ten_paper_research_20260621` and does not replace protected fields. `core/canonical_runtime_20260617.py` publishes the same object to the existing one-way compatibility adapter. Tabs and renderers read that published generation; they do not call research builders.

Atomicity remains centralized in `services/canonical_snapshot_store.py`. The custom research bundle is popped from `BUNDLE_KEY = "__research_validation_20260621__"` and inserted inside the same `BEGIN IMMEDIATE` transaction as the canonical snapshot. A staged failure rolls back both canonical and research rows.

## Existing mechanisms found and preserved

The existing package already contained research mechanisms for conformal prediction/risk control, multicalibration, proper scoring, Bayesian/PELT changepoints, adaptive windows, dynamic model averaging, method confidence sets, PBO, Deflated Sharpe Ratio, uncertainty decomposition, DLinear challengers, MMD/label-shift checks, DML/IRM/Group-DRO, Random Cut Forest, signatures/Matrix Profile/MPdist/constrained DTW, TinyLFU, M4 aggregation, canonical atomic publication, and completed-H1 validation. The new code does not rename or duplicate those modules.

## Lunch 4A/4B protection

`ui/lunch_four_core_fields_20260619.py` keeps one visual placement gate and an exclusive dispatcher:

- 4A calls `_render_workspace_4a`: Similar-Day/pattern intelligence + current canonical data + its history browser.
- 4B calls `_render_workspace_4b`: regime/combined logic + its history browser.

Their renderer functions, state selection, imports, calculations, and history keys remain separate. The new explanation display is a read-only addition inside the existing Decision 11 explanation area. It imports no builder and starts no calculation.

## New integration boundary

Exactly one production call to `build_ten_paper_research_transaction(...)` exists, in `core/settings_run_orchestrator_20260617.py`, after settled evidence is available and before pre-publication validation. Static scans found zero builder references under `ui/`, `tabs/`, and `pages/`.

## Data and leakage boundaries

The new layer:

- filters to settled rows and completed H1 data;
- sorts chronologically;
- uses two chronological windows with purge/embargo of at least six rows, matching the maximum forecast horizon used by the gate;
- contains no negative shift, centered rolling window, future backfill, random split, or full-sample scaler pattern;
- bounds settled evidence to 3,000 rows, FDR tests to 240, feature count to 24, and provenance nodes to 768;
- stores compact dictionaries/lists in canonical state and no DataFrames in session state;
- does not train a heavy model during rendering.

## Failure behavior

All ten techniques start in SHADOW. If a technique lacks sample support or assumptions, the transaction publishes `INSUFFICIENT_EVIDENCE`, leaves protected outputs unchanged, and keeps `production_influence_enabled = false`. BUY can only remain BUY or be shadow-downgraded to WAIT; SELL can only remain SELL or be shadow-downgraded to WAIT; protected WAIT is never promoted.

## Architecture conclusion

The implementation is additive and located at the correct transaction boundary. It extends the existing atomic history bundle and canonical adapter without creating a second publication authority, a second Run button, a new top-level UI route, or a renderer-side research path. Production benefit remains unverified until real settled evidence passes every gate in two independent chronological windows.
