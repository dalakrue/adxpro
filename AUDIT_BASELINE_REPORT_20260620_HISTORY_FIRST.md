# Audit and Baseline Report — History-First Performance Hardening

## Scope inspected

The supplied ZIP contained **726 original files**. The final source tree contains **471 Python modules** after additive implementation. A full AST/static scan found **3,007 functions**, **2,478 imports**, **899 Streamlit widget calls**, **729 session-state references**, **394 renderer calls**, **18 probable network call sites**, and **0 Python parse errors**. The complete location-level inventory is in `AUDIT_INVENTORY_20260620.json`; database schemas are in `DATABASE_SCHEMA_INVENTORY_20260620.json`; cache definitions are in `CACHE_INVENTORY_20260620.json`.

Baseline source scan before changes: 460 Python files, 2,918 functions, 897 widgets, 18 decorated caches, 15 probable network sites, 728 session-state references, and 380 renderer calls. Copy counts are not compared because the baseline and final scanners used different AST matching breadth.

## Active entry and page graph

`app.py` is the preferred entry. It calls `adx_dashpoard.main`, then `core.app_shell.run_app`, then `core.app.runner.run_app`. The selected page is loaded through `core.app.routes.load_tab` and `tabs.antd_page_router_20260615.show`.

Top-level registry routes: Settings, Lunch, Dinner, Morning, Research, Other, plus backward-compatible Home, Data Visualization and AI Assistant aliases. The active router renders only Settings, Lunch, Dinner, Morning, Research or Other. Existing Other inner workspaces remain Engine, Train Data, Database, Pre Original, Backtest and Profile. Lunch inner routes remain Full Metric Details + History, PowerBI Projection, Priority + Decision + Reliability, Finder and the authoritative six-field default surface.

## Renderer defects confirmed before modification

1. Closed Lunch `st.expander` blocks executed their Python bodies, so all six heavy sections were instantiated on every rerun.
2. Lunch Field 5 called the current-data renderer a second time.
3. Morning imported the large legacy `tabs.home` module chain before the user opened the workspace.
4. Research imported advanced analysis/NLP work for unrelated selected workspaces.
5. Chart histories could serialize much more data than a phone or browser needed.
6. History evidence had overlapping schemas and no universal event-time/run identity across every field.

## Static UI and execution inventory

The location of every detected `st.expander`, `st.tabs`, `st.toggle`, `st.button`, radio/segmented-style call, data frame, chart, cache decorator, copy, SQL call, renderer call and probable network call is machine-readable in `AUDIT_INVENTORY_20260620.json`. This is intentionally not duplicated as a 900-row Markdown list.

## Session-state and memory baseline

The scan found 729 state references. Runtime sizes cannot be truthfully inferred from source alone. The implementation therefore prevents new unbounded history frames in session state, retains large immutable evidence in SQLite, limits display frames, uses shallow copies/projection, and records measured Python allocation/RSS in `performance_history`. Existing application state keys were preserved.

## Data stores

Four SQLite stores remain: `data/adx_runtime_store.sqlite3`, `data/adx_similarity_store.sqlite3`, `data/canonical_runtime.sqlite3`, and `data/quant_app.sqlite3`. SQLite integrity is recorded per file in `DATABASE_SCHEMA_INVENTORY_20260620.json`. CSV/JSON/text assets remain untouched. No small table was migrated to Parquet for appearance.

## Network and secret boundary

Probable network call sites are listed in the audit JSON. New history/render code performs no network request. API values are redacted before AI history persistence; cache keys accept identity metadata only; no secrets are written to the new tables, logs or exports.
