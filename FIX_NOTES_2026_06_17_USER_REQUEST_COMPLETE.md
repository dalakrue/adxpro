# M1 ADX Quant Pro — Restore, Sync and Error-Fix Build (2026-06-17)

Run with:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Navigation and layout

- Restored the native Streamlit sidebar as a clean Liquid Menu and made app-level sidebar hiding a compatibility no-op.
- Restored the **Other** workspace with Engine, Train Data, Database, Pre Original, Backtest and Profile inner tabs.
- Fresh sessions open **Settings** first.
- Top-level menu contains only Settings, Lunch, Dinner, Morning, Research and Other. Legacy Home, Data Visualization and AI Assistant routes are mapped internally and are not shown as top-level buttons.
- Reduced the fixed scrolling menu control to 28 px desktop / 32 px mobile; it remains fixed while scrolling.
- Phone/Laptop UI controls remain inside the menu. Phone mode enlarges controls, inputs, metrics, expanders and data tables.

## Canonical calculation synchronization

- Added `core/decision_policy_20260617.py` as one shared BUY/SELL/WAIT/NO TRADE reconciliation policy.
- Generic `RANGE_EXPANSION` no longer automatically becomes WAIT. It uses the existing latest H1 close movement to select BUY/SELL when directional evidence exists.
- Lowered BUY/SELL gates and made WAIT/NO TRADE stricter while preserving severe-risk protection.
- Full Metric Details publishes its exact major-regime history to the shared canonical cache.
- Canonical regime selection now discovers dynamically named Full Metric / major-regime history tables and prioritizes structurally complete, current tables.
- Lunch, Finder, PowerBI, Research and AI use the same current regime, regime start/end, decision, reliability, error and priority snapshot.

## Lunch and 10-day backtest

- Lunch Quick Decision is route-guarded to Lunch only.
- Quick Decision displays synchronized `st.metric` cards and exactly one merged table.
- Merged table includes Time, Hour, Major Regime, Regime Start, Regime End, Regime True/False, Decision, KNN Priority, Greedy Priority, score, reliability, error, movement and NLP fields.
- KNN and Greedy priorities are ascending.
- The same 10-day EURUSD H1 table is duplicated at the bottom of Lunch inside an Open/Close expander for manual backtesting.
- Copy controls are not rendered inside Quick Decision.

## PowerBI error and regime fields

- Current Regime, Regime Start and Regime End are read from the same canonical major-regime history as Full Metric Details.
- Prediction error reads completed prediction-vs-actual summary or row data first.
- A stale or missing `0.00%` is never presented as verified accuracy. The UI shows a recent-H1 volatility proxy with a clear Proxy label, or N/A when neither actual history nor a valid proxy exists.

## Settings, NLP and AI Assistant

- Settings includes the second NLP/LLM key, endpoint and model configuration.
- Added Connect NLP and Connect Market + NLP Together controls.
- NLP connection is shared by Research, NLP calculations and optional AI Assistant LLM answers.
- AI Assistant keeps 1,000+ prepared question patterns, exact-question intent routing, local fallback and optional grounded external LLM answering.
- Removed the always-prominent Safer Bias status from the general AI header. Directional bias is added only when the question is directional.
- Data Mining and Research NLP/Data Mining show the synchronized 10-day Regime + NLP + KNN/Greedy table.

## Copy/export and structured result display

- Copy Short is curated to important canonical data and limited to 6,500 characters for practical chat input.
- Copy Full includes the synchronized 10-day table plus current cached system data.
- Structured dictionaries, lists, Series and DataFrames passed to Streamlit `write/json` are rendered as tables instead of raw calculation text.

## Validation performed

- `python -m compileall -q .` — passed.
- `python tools/validate_final_sync_20260617.py` — passed.
- `python tools/validate_architecture.py` — passed.
- Synthetic validation covered RANGE_EXPANSION directional reconciliation, Full Metric regime start/end, current-open segment behavior, mixed timezone data, 10-day table columns/sorting, NLP hour matching, actual prediction error extraction, proxy fallback and N/A behavior.

The build environment used to package this ZIP did not include the `streamlit` command-line executable, so a live browser launch could not be performed here. The project includes Streamlit in `requirements.txt`; install dependencies before running.
