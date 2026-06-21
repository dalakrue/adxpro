# UI Changelog — 2026-06-14

## Future-proof UI Shell Upgrade

- Added `app.py` as a future preferred entry point while keeping `adx_dashpoard.py` and `main.py` compatible.
- Added `ui/` package for display/control layer helpers.
- Added central navigation registry.
- Added permanent session-state main-page drawer with one Menu / Close toggle.
- Added central mobile CSS injector for rounded cards, soft shadow, large buttons, and iPhone spacing.
- Added top status bar.
- Added UI Health Check panel.
- Added Future Safety Guard for session state initialization, required-file checks, export path validation, and safe active-page fallback.
- Added best-effort duplicate literal widget key scanner for future cleanup reports.
- Added safe export path helpers.
- Kept native Streamlit sidebar as backup only.

## Protected

No trading calculation, prediction, ML table, history table, chart data, JSON output, export data, KNN, Greedy, PowerBI, NLP, regime, reliability, priority, or AI answer logic was intentionally changed.


## 2026-06-14 16:49:36 — Logic Safety Guard + Hidden Danger Engine
- Added additive logic-safety wrapper modules.
- Added hidden danger detector, no-trade guard, prediction drift monitor, regime age warning, conflict matrix, calibration, data quality guard, lookahead bias guard, signal stability, reason chain, shadow comparison, and audit table.
- Original calculations and display sources were not intentionally changed.
- Python compile check passed; ZIP integrity check passed after packaging.
- Heavy checks run only after Run Safety Check.

## 2026-06-14 — Sidebar Hard Fix + Main-Page Sidebar Controls
- Added `ui/native_sidebar_js.py` with optional JavaScript open/close/toggle for the native Streamlit sidebar.
- Added `ui/sidebar_fallback_panel.py` so API/data connection, timer, UI mode, and account controls work inside the main-page drawer even if the native sidebar cannot open.
- Updated `ui/main_menu_drawer.py` to show native sidebar open/close helper buttons and the expanded main-page sidebar controls.
- Updated `core/ui/styles.py` to disable the old permanent sidebar force-hide CSS that could prevent opening after Guest/Login.
- Updated `core/app/runner.py` so native sidebar errors no longer stop the app; the main-page drawer continues working.
- Existing trading logic, calculations, ML tables, regime logic, safety engine, copy/export, and tab sources were not intentionally changed.

## 2026-06-15 — Long-Term UI Stability Fix

- Added Home Top Control Panel as the real stable control center.
- Kept native Streamlit sidebar as backup only; no fragile sidebar DOM open/close JavaScript.
- Duplicated main navigation in the top control panel using session_state.
- Added central copy engine with clipboard + download/text fallback.
- Routed existing mobile copy button imports through the central copy engine.
- Removed fake fallback preserved-copy messaging from the main menu path.
- Rebuilt AI Assistant final UI around `st.chat_input` so pressing Enter answers directly.
- Made prepared choice-box questions answer immediately on selection change.
- Kept Analysis as optional advanced rerun only.
- Consolidated Local NLP diagnostics into one clean expander.
- Added AI inner tabs: Chat, Local NLP, Data Mining, Deep Analysis, History.
- Added defensive modern UI library adapter for AntD, shadcn-ui, modal, and AgGrid.
- Added one session_state Lunch/Home update status card instead of repeated status panels.
- Protected trading logic, calculations, ML logic, prediction outputs, tables, charts, exports, and copy content.

## 2026-06-15 Liquid Glass / NLP / Alpha-Delta Stability Upgrade

- Added a Liquid Glass CSS theme layer using normal Streamlit/CSS only; no fragile JavaScript DOM sidebar hacks.
- Reworked the top Home control area into a compact rail with Menu, Run All, and central-copy buttons.
- Rebuilt the app drawer/sidebar control as a session_state-controlled Liquid Glass drawer with Menu, Connector, Timer, Copy, and UI/Sidebar sections.
- Kept native Streamlit sidebar hidden/backup by default so the app can work even when native sidebar behavior changes.
- Added a lightweight local NLP pipeline: normalization, tokenization, stemming, lemmatization, stopword removal, POS tagging, dependency parsing, constituency parsing, NER, WSD, coreference, mention/entity/relation extraction, topic detection, summarization, and text generation.
- Added the NLP pipeline to both AI Assistant Local NLP and Research/Home NLP displays.
- Added display-only alpha/delta/data-point diagnostics for PowerBI blue-vs-red projection paths and regime projection paths.
- Adjusted AI Assistant local explanation bias to make WAIT much harder and BUY/SELL easier, without changing trading engines or ML prediction formulas.
- Removed the final AI chat Analysis button flow; Enter and choice-box selection answer directly.
- Added architecture documentation for future upgrade/downgrade compatibility and UI isolation.
