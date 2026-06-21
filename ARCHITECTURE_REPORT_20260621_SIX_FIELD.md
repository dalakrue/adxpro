# Architecture Report — Six-Field Lunch Upgrade

Date: 2026-06-21  
Package: ADX Quant Pro EURUSD H1  
Entry point: `app.py` → `adx_dashpoard.py` → `core.app_shell.run_app` → `core/app/runner.py`

## Audited execution boundaries

The protected Run Calculation transaction remains in `core/settings_run_orchestrator_20260617.py`. Its SHA-256 is unchanged from the uploaded package. The canonical publication and completed-H1 authority remain in `core/canonical_runtime_20260617.py`, `core/decision_product_engine_20260617.py`, and the existing shared-sync/prediction-ledger modules. Lunch, menu, refresh, copy, AI, future-strategy history, and presentation-cache changes are consumers of a completed canonical generation; they do not create an alternative decision transaction.

## Active UI path

`tabs/final_lunch_upgrade_20260617.py` now calls `render_lunch_six_core_fields()` in `ui/lunch_four_core_fields_20260619.py`. The old public callable remains as a compatibility alias, but it also renders the six-field implementation. No new top-level page, tab, sidebar item, or route was added.

## Six principal load gates

1. Full Metric 25-Day History + Decision Tables
2. Power BI Price Prediction Path
3. 25-Day Regime History + Lower / Medium / Higher Standards
4. Dinner Full Combined Intelligence
5. Grounded AI Assistant
6. Future Strategy Research History

Each gate uses a persistent non-widget state key plus a widget callback. Closed fields do not import their field-specific renderer. Phone mode supports exclusive-open behavior. Toggle callbacks never call the Settings orchestrator.

## Data and history path

`core/history_query_20260621.py` adds a completed-H1, 25-day, selected-column query boundary. It uses DuckDB projection/predicate/limit pushdown when DuckDB is available and a vectorized pandas fallback otherwise. Field 3 selects regime-related columns before querying. Historical views remain newest completed H1 first and reject future rows.

## Refresh path

The menu now exposes three separate actions: Refresh Data, Run Calculation, and Reduce RAM. `core.connectors.data_parts.session.refresh_now()` is the public forced connector path. `core/app/refresh.py::refresh_data()` refreshes and validates source data, changes the source signature, marks dependent calculations stale, preserves the last completed canonical generation, and clears only reconstructable presentation caches. It does not call Run Calculation.

## Copy/export path

`services/canonical_exports.py` is the only payload builder used by the menu and the optional Field 6 canonical export. Short and All payloads are generated only after the corresponding button is pressed. The machine-readable JSON remains a separate explicit action.

## AI path

Field 5 imports `tabs/ai_assistant_compact_20260619.py` only when Field 5 is open. Evidence retrieval and answer planning run only after Send / Analyze. The pipeline is local, bounded, read-only, and generation-grounded. No external AI API, embedding service, or heavy language model was added.

## Cache/resource path

`core/adaptive_presentation_cache_20260621.py` is a bounded session-local presentation cache. It never contains the protected calculation result. Reduce RAM may clear charts, prepared copy text, search/retrieval results, temporary DataFrames, and closed-field presentation state, while preserving canonical results, settled evidence, database history, connector configuration, and user settings.

## Deployment

`requirements.txt` continues to target Streamlit Cloud and Python 3.12. The upgrade uses existing pandas, NumPy, DuckDB, and standard-library dependencies; it adds no paid or heavy-model package.
