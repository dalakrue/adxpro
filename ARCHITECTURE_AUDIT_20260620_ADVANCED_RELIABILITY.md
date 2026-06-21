# Architecture Audit — Advanced Reliability and Distribution Shift v2

**Audit date:** 2026-06-20  
**Project:** EURUSD H1 Streamlit application  
**Preferred entry:** `app.py` → `adx_dashpoard.main()` → `core.app_shell.run_app()`

## Inspection scope and method

The uploaded ZIP was recursively inventoried and mechanically scanned. The completed package contains 460 Python files and approximately 75,409 Python source lines after this upgrade, four SQLite databases, configuration/runtime files, tests, pages/tabs, compatibility adapters, persistence services, and historical reports. All active Python files were compiled. Deep call-path inspection focused on every component that can affect calculation, settlement, publication, synchronization, persistence, or existing visible rendering. Static searches were also run for prohibited leakage patterns and renderer-side research calculation.

This audit does not claim that every historical/legacy duplicate contains unique executable logic; the project contains compatibility wrappers and archived implementations. The active execution path and affected compatibility paths were traced and tested.

## Existing authoritative flow

1. `app.py` imports `adx_dashpoard.main` and provides a cloud-safe project-root path.
2. `adx_dashpoard.py` delegates to `core.app_shell.run_app()`.
3. The existing Settings **Run Calculation** action invokes `run_settings_calculation()` in `core/settings_run_orchestrator_20260617.py`.
4. The orchestrator performs connector/data-quality work and creates a completed-UTC-H1 frame.
5. Pending prediction and trust outcomes are settled near the start of that same transaction.
6. Existing Full Metric Detail + History, reverse-10 evidence, regime, priority, KNN, Greedy, Power BI paths, NLP, reliability, first-generation research calibration, risk stack, and Similar-Day evidence are assembled into one canonical object.
7. The new v2 transaction runs once, after settled evidence is available and immediately before `publish_canonical_atomically(...)`.
8. `publish_canonical_atomically(...)` validates, snapshots, checksums, and publishes the generation.
9. Only after successful canonical publication is the staged v2 SQLite snapshot marked `PUBLISHED`.
10. Existing Lunch, Dinner, Finder, Data Visualization, Reliability, Research, NLP, and AI adapters read the same published object; tab navigation does not execute v2 research.

## Exact insertion point

The insertion is in `core/settings_run_orchestrator_20260617.py`, between Similar-Day completion and `publish_canonical_atomically(...)`.

Inputs reused:

- `final_df`: the already-cleaned completed-H1 frame from the current Run Calculation transaction.
- `settled_research_predictions`: one bounded chronological settled-prediction frame already assembled for existing settlement/research work.
- `canonical`: the complete pre-publication canonical mapping.

No renderer calls the builder. No new Run Calculation action exists. No large DataFrame is placed in session state by the new layer.

## Atomic transaction design

`core/advanced_reliability_shift_20260620.py` returns:

- an additively updated canonical mapping;
- a display-independent compact research result;
- a staging status.

The SQLite row is first written as `STAGED`. The canonical validator checks calculation ID, generation, latest completed H1 timestamp, completed-H1-only contract, and no-reversal policy. After the canonical snapshot commits, the matching row is changed to `PUBLISHED`. A failed canonical publication leaves no published research pointer.

## Adapter publication

`core/canonical_runtime_20260617.py` exposes the same v2 payload to existing:

- `current`
- `reliability`
- `powerbi`
- `data_mining`
- top-level shared adapter
- `ai_grounding`

The adapters do not recalculate. Existing central red, yellow, and blue Power BI path fields are not rewritten by the v2 transaction.

## Data and persistence inventory relevant to the change

- `data/quant_app.sqlite3`: app events plus the two new research tables.
- `data/canonical_runtime.sqlite3`: atomic canonical snapshots, run registry, performance traces.
- `data/adx_runtime_store.sqlite3`: compact canonical summaries, frame manifests, AI conversation rows.
- `data/adx_similarity_store.sqlite3`: Similar-Day generations and feature store.

The v2 layer stores one compact JSON snapshot and one bounded signature vector per calculation ID. It does not persist duplicate OHLC or settled DataFrames.

## Protection findings

- Full Metric Detail + History remains the primary calculation authority.
- Directional market view is not changed by v2.
- A BUY or SELL can only remain unchanged or have tradeability downgraded to WAIT by the final CRC gate.
- Priority retains the protected original score and receives a separate capped research-adjusted score on the same scale.
- Existing score meanings, Full Metric fields, Alpha/Delta, regime, KNN, Greedy, Similar-Day, NLP, history, copy/export, API/authentication/timer/logout/mobile logic remain in place.
- No new top-level tab, page, sidebar item, menu item, Lunch principal field, visible section, or duplicate button was added.

## Correctness controls

- explicit completed-candle cutoff;
- sorted, unique chronological inputs;
- bounded OHLC/settled windows;
- no negative shift, centered rolling window, future backfill, random split, or full-sample scaler in the v2 module;
- deterministic hash-derived random seeds;
- chronological purge/embargo for DML;
- minimum sample and hierarchical fallback rules;
- assumption rejection for BBSE under strong feature drift;
- copy-on-write nested forecast update, preventing mutation of the protected pre-research canonical object.

## Operational limitations

A full live broker/API calculation was not executed because no live credentials were supplied. Streamlit startup and health were verified locally. Production accuracy, causal event effects, and mobile device temperature were not claimed.
