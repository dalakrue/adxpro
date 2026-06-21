# M1 ADX Quant Pro — Final Restore, Sync and Error-Fix Build

## Start the app

```powershell
streamlit run app.py
```

`main.py` and `adx_dashpoard.py` remain compatible fallback entry points.

## Navigation, sidebar and phone UI

- Fresh Streamlit sessions open on **Settings**.
- Restored native Streamlit sidebar in expanded mode with the clean Liquid Menu.
- Visible top-level routes are only: Settings, Lunch, Dinner, Morning, Research and Other.
- Removed Home, Data Visualization and top-level AI Assistant from the visible menu; their useful renderers remain routed inside existing pages.
- Restored Other inner workspace: Engine, Train Data, Database, Pre Original, Backtest and Profile.
- Reduced the fixed menu control to a compact 32 px desktop / 36 px phone button that remains fixed while scrolling.
- Phone/Laptop controls live inside the floating/sidebar menu only.
- Phone mode now enlarges buttons, inputs, metrics, tables and expanders substantially.

## Lunch Quick Synced Decision

- Strict Lunch-only route guard; it cannot render on Settings/Home or another top-level page.
- Reads one canonical shared result used by Lunch, Power BI, Finder and AI grounding.
- Prefers complete major-regime/full-metric history and synchronizes regime, direction, decision, start/end, reliability, data quality and error.
- RANGE_EXPANSION uses current H1 price momentum instead of being forced to WAIT.
- Directional display gate is synchronized at reliability >=38 and usable data; NO TRADE is reserved for severe risk or materially weak evidence.
- Quick output contains st.metric cards and one merged EURUSD H1 table only; no quick-section raw JSON, copy control or duplicated full-backtest block.
- KNN and Greedy priorities are sorted ascending.
- Added table metrics for rows, 10-day window, latest H1 time and priority order.
- The reusable 10-day Regime + NLP + KNN/Greedy expander appears below Lunch content.
- Historical regime TRUE/FALSE is validated per segment.
- NLP news is attached only to its matching historical hour.

## Regime and Power BI correctness

- Current Regime, Regime Start and Regime End use the same canonical source everywhere.
- Mixed timezone API candles and stored regime-history timestamps are normalized before comparison, preventing live-data crashes.
- Average error now displays actual prediction-vs-actual feedback when samples exist.
- When completed samples do not exist, the UI clearly labels a recent-H1 volatility **proxy** instead of presenting it as actual accuracy.
- When neither actual feedback nor a valid proxy exists, the value is N/A rather than an impossible 0.00%.
- Power BI reliability warnings distinguish actual feedback from proxy data.

## Settings and NLP/LLM connection

- Settings contains market API fields plus NLP/LLM key, endpoint and model fields.
- Added **Connect Market + NLP Together** while retaining separate NLP connect/disconnect controls.
- The NLP connection enables Research NLP calculations and AI Assistant provider answers; local NLP remains the safe fallback.
- Connection status is displayed with metrics and a table rather than one raw status string.

## AI Assistant and 1,000-question box

- Validated **1,203 prepared question patterns**.
- Added a dedicated system/control intent for sidebar, menu, Settings, APIs, phone UI, copies, Finder, Research and Other workspace questions.
- Non-trading questions no longer show unrelated Safer Bias, TP or Main Risk sections.
- Trading questions still receive direction, entry, hold, TP and risk sections grounded in synchronized data.
- Optional external LLM answers are re-grounded after the provider response.
- Copy Short is curated to the most important current regime, decision, reliability, error, priority, NLP and OHLC values and capped at 7,000 characters.

## Structured output

- Added an app-wide compatibility guard that turns dictionaries, Series, DataFrames and list-of-record calculation outputs passed through `st.write`/`st.json` into tables.
- Normal explanatory text and existing charts/widgets remain unchanged.

## Validation completed

- Full Python compileall: passed.
- Architecture validator: passed.
- Final synchronization validator: passed.
- Mixed timezone runtime test: passed.
- Stale closed-regime/current-regime reconciliation test: passed.
- RANGE_EXPANSION directional-decision test: passed.
- Actual/proxy/N/A error behavior tests: passed.
- 10-day hourly limit and NLP hour-matching tests: passed.
- Settings-first/menu/Other workspace contracts: passed.
- AI system-question, quality-question and directional-question relevance tests: passed.
- ZIP integrity test: passed before delivery.

External LLM behavior still depends on the provider endpoint, key, model compatibility and internet access entered in Settings. When unavailable, the local grounded answer is used instead of crashing.
