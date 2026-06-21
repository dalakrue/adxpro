# ADX Quant Pro / new7 — EURUSD H1 Canonical Upgrade Report

Date: 2026-06-18

## Main result

The existing **Full Metric Detail + History** calculation is now the primary operational authority. Its implementation file, formulas, thresholds, tables, reverse-decision factors, and history behavior were not modified. SHA-256 remained:

`fe0797ab30f469f3ea748bc66a690b18a68aaf91306ac33c797bdcdcf6e60682`

The existing canonical runtime was consolidated rather than replaced. Full Metric output is adapted one-way into one transactional canonical generation consumed by Lunch, Dinner, Finder, Research, Power BI support fields, Reliability, NLP support fields, and AI Assistant.

## Files changed

- `core/canonical_runtime_20260617.py`
- `core/decision_product_engine_20260617.py`
- `core/regime_sync_20260617.py`
- `core/settings_run_orchestrator_20260617.py`
- `tabs/ai_assistant_lite.py`
- `tabs/dinner_morning_data_patch_20260614.py`
- `tabs/dinner_unified_center_20260617.py`
- `tabs/dv_research_alignment_20260612.py`
- `tabs/final_research_projection_auth_sync_20260612.py`
- `tabs/reliability_control_center_20260614.py`
- `tabs/research.py`

## Files added

- `core/full_metric_canonical_adapter_20260618.py`
- `core/research_causality_20260618.py`
- `tests/conftest.py`
- `tests/test_full_metric_canonical_sync_20260618.py`

## Canonical source and redirected calculations

- Canonical primary source: protected `tabs/eurusd_h1_matrix.py` Full Metric result and Full Metric History.
- The orchestrator now stages Full Metric, forecasts, regime, reliability, Research/NLP confirmations, and candidate ranking, then publishes one complete generation atomically.
- Forecast direction, Research, NLP, KNN, Greedy, regime, Power BI, and M1 cannot reverse the Full Metric H1 direction.
- Local AI Assistant session-state searching was replaced by direct canonical grounding after a valid run.
- Reliability rendering prefers the shared canonical result and does not rebuild a competing percentage on tab switches.
- Finder and all priority consumers use the same published canonical priority DataFrame.
- Dinner master/decision fields prefer canonical Full Metric values instead of older Power BI caches.

## EURUSD H1 and M1 protections

- Operational identity is fixed to `EURUSD` / `H1`.
- Data-quality validation excludes an incomplete final H1 candle.
- Every operational adapter carries the same run ID, generation, signature, symbol, timeframe, and latest completed H1 timestamp.
- M1 remains timing/confirmation only. Conflict changes tradeability to WAIT; it cannot turn BUY into SELL or SELL into BUY.

## Two-opportunity synchronization

- Candidate base ranking uses Full Metric History with the requested composition: Master 30%, Entry 25%, stronger directional score 15%, Hold 10%, TP 10%, inverse Exit Risk 10%.
- KNN, Greedy, Research, NLP, regime, and reliability are capped confirmation adjustments and gates.
- Up to two current-day candidates are published once and reused everywhere.
- Candidate 2 requires time separation or a material setup improvement/change.
- Missing or failed expected-value/reliability confirmation remains WATCH, never a forced entry.
- The current candidate can become QUALIFIED only after the existing downstream expected-value, reliability, data-quality, conflict, forecast, and timing gates pass.

## Research, NLP, Random Forest, and walk-forward repairs

- Next-candle labels use nullable targets; unknown final future rows are excluded rather than converted to false down/SELL labels.
- Existing Random Forest Research paths now use time-ordered purged splits, never random shuffling.
- Historical news uses backward as-of publication joins, enforcing `publication_time <= decision_time`.
- Synthetic/educational timestamp fallback was removed from operational Research loaders.
- Educational fallback cannot publish a canonical operational decision.

## Performance improvements

- One main Settings Run Calculation remains the heavy calculation trigger.
- 1-day, 5-day, and 25-day regime tables build only during that main run; tab switching is read-only.
- Canonical DataFrames are reused across priority consumers.
- Full session-state scans were removed from Dinner audit and AI grounding.
- Previous valid canonical generation remains available until a complete new generation validates and publishes.
- Mobile rendering limits displayed rows without deleting server-side history.

## Validation performed

- Python compile-all: PASS (all Python files).
- Automated tests: **53 passed**.
- Internal import resolution: 139 project imports checked, 0 missing.
- Critical clean imports: PASS.
- Streamlit HTTP startup/health endpoint: PASS (`ok`).
- Streamlit AppTest login/guest startup: PASS, 0 exceptions.
- Top-level routes Settings, Lunch, Dinner, Morning, Research, Other: PASS, 0 exceptions.
- Existing Lunch, Dinner, and Research inner routes: PASS in not-ready/cached mode, 0 exceptions.
- Protected Full Metric SHA-256 comparison against uploaded ZIP: PASS, byte-identical.

## Remaining limitations

- A live MT5/Doo Prime feed was not available in the test container, so live broker data retrieval was not exercised.
- A Finnhub API key was not supplied, so authenticated live-news connectivity was not exercised; cached/local and not-ready behavior remains protected.
- Real-money outcome quality cannot be guaranteed by software tests. The tests verify synchronization, causality, routing, safety gates, and application startup.

## Main entry and command

Main file: `app.py`

```bash
streamlit run app.py
```
