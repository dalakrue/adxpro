# Full Metric, Dinner AI, and Research NLP Restoration — 2026-06-18

## Completed changes

- Preserved the protected Full Metric producer and formulas unchanged.
- Hardened the active shared Full Metric renderer so a malformed Entry table cannot stop Direction, Hold, Exit, TP, regime, factor-history, or complete history tables below it.
- Restored the complete Full Metric History view with the latest valid completed H1 candle first and no display truncation of the protected history.
- Consolidated the default Lunch restoration path onto the same shared Full Metric renderer, with the prior renderer retained as a safe fallback.
- Restored Dinner inner navigation as Regime Summary, Combined Logic, and AI Assistant, and connected AI Assistant to the existing Dinner chat renderer.
- Moved the Research NLP connector status, controls, and ranked news workspace to the top of the NLP inner tab.
- Removed the duplicate legacy Research API/password field; API-key management remains in Settings/sidebar.
- Moved the old one-row NLP snapshot into a collapsed legacy detail field so it no longer replaces the ranked table.
- Expanded the real-news fallback across multiple forex and macro RSS/Atom sources. It targets at least 10 unique real articles, then uses the existing ranking and impact pipeline. It never fabricates news when external sources are unavailable.

## Modified files

- `ui/full_metric_shared_renderer_20260618.py`
- `ui/lunch_restored.py`
- `tabs/research.py`
- `ui/nlp_research_panel.py`
- `tabs/final_research_projection_auth_sync_20260612.py`
- `ui/antd_navigation_20260615.py`
- `core/tab_state_stability_20260615.py`

## Added test file

- `tests/test_full_metric_dinner_nlp_restore_20260618.py`

## Validation results

- Python compileall: passed.
- Pytest: 83 passed.
- Architecture validator: passed.
- Final synchronization validator: passed.
- Finnhub/NLP/Lunch/Research validator: passed.
- Streamlit HTTP health and root-page smoke test: passed.
- Streamlit AppTest login/guest/dashboard: 0 exceptions, 0 errors.
- Direct Dinner AI AppTest: 0 exceptions, 0 errors; Dinner AI marker rendered.
- Protected producer SHA-256 remained `fe0797ab30f469f3ea748bc66a690b18a68aaf91306ac33c797bdcdcf6e60682`.

## Run command

```bash
streamlit run app.py
```
