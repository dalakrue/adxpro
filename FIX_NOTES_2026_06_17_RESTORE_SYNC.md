# M1 ADX Quant Pro — Restore, Sync, and Mobile UI Fix (2026-06-17)

## Navigation and UI
- Fresh sessions open on **Settings**.
- Visible top-level navigation is: Settings, Lunch, Dinner, Morning, Research, Other.
- Home, Data Visualization, and top-level AI Assistant buttons are removed from visible navigation; their useful renderers remain available inside Lunch/Dinner/Research.
- Restored native sidebar with a narrower responsive width and the same compact Liquid menu.
- Restored Other workspace: Engine, Train Data, Database, Pre Original, Backtest, Profile.
- Phone/Laptop display control is inside the menu. Phone mode enlarges controls and metrics.
- The three-dot menu rail is compact and sticky while scrolling.

## Lunch, regime, PowerBI, and priority sync
- Added one canonical regime snapshot used by Lunch, PowerBI metrics, and AI context.
- Current regime is read from latest major-regime history before stale generic state.
- Regime start/end, validation, reliability, and average prediction error use the same source.
- A missing/zero completed prediction error is displayed as a clearly labeled recent-H1 volatility proxy until feedback history exists; it is not displayed as impossible 0.00%.
- Lunch Quick Synced Decision has a strict Lunch-only route guard.
- Lunch quick output uses metrics and one merged table; no quick-section copy button or raw JSON/text data output.
- Added a 10-day Regime + NLP + KNN/Greedy hourly table and reusable open/close backtest field.
- Finder reads the same 10-day table and sorts KNN/Greedy priorities ascending.
- Central decision policy allows directional BUY/SELL from reliability 45 with acceptable exit risk; WAIT requires weak/flat evidence; NO TRADE requires severe risk or reliability below 35.

## Settings, NLP, and AI Assistant
- Added NLP/LLM API key, endpoint, model, Connect, and Disconnect controls beside market API settings.
- External LLM use is optional and uses a local fallback when unconfigured or unavailable.
- Prepared-question library remains above 1,000 patterns.
- Added high-precision intent overrides so prediction error, reliability, regime, and data questions do not receive unrelated BUY/SELL advice.
- Trading questions still receive direction/entry/hold answers grounded in the latest shared result.
- Research NLP history is extended to 10 days, with table/metric rendering for key results.

## Compatibility repair
- Added missing compatibility re-exports required by the split Pre Original legacy modules.
- Preserved existing calculation modules, histories, exports, models, and original PowerBI renderer behind run/load gates.

## Validation completed
- Full Python `compileall`: passed.
- Architecture validator: passed.
- Key modified-module import test with a Streamlit compatibility stub: passed.
- Settings-first navigation and legacy Home-to-Lunch normalization: passed.
- RANGE_EXPANSION major-regime sync test: passed; stale NO TRADE became the momentum-aligned directional decision.
- Non-zero prediction-error fallback test: passed.
- AI 1,203-pattern test and non-trading intent guard: passed.
- Lunch-only route guard: passed.
- Restored Other inner-module import/callable checks: passed.

Run with:

```powershell
streamlit run app.py
```

`main.py` and `adx_dashpoard.py` remain compatible alternative entry points.
