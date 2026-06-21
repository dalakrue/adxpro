# ADX Quant Pro Decision Product Upgrade — 2026-06-17

## Confirmed runtime path

- Preferred command: `streamlit run app.py`
- Runtime chain: `app.py` → `adx_dashpoard.main()` → `core.app_shell.run_app()` → `core.app.runner.run_app()`
- Active route registry: `core/app/registry.py`
- Existing top-level routes were preserved. No new top-level page, tab, sidebar, or navigation item was added.

## Internal dependency map

1. Settings main Run button calls `core.settings_run_orchestrator_20260617.run_settings_calculation()` exactly once.
2. Existing Lunch/PowerBI/regime/NLP engines build their normal cached outputs.
3. `core.adx_shared_sync_20260615.ensure_shared_calculation_result()` provides the legacy shared adapter.
4. `core.decision_product_engine_20260617.build_decision_result()` validates completed OHLC data and builds one immutable canonical `DecisionResult` for 1h/2h/3h/6h.
5. `core.prediction_ledger_20260617.PredictionLedger` settles due outcomes before writing the next run, then stores runs, predictions, regime snapshots, outcomes, drift history, and NLP event memory.
6. Lunch, PowerBI, Regime Summary, Settings diagnostics, Backtest, and Train Data read the same canonical result through UI adapters.
7. Research → NLP renders the same optional session-only Finnhub connector and remains operational without a key.

## Implemented reliability upgrades

- Typed canonical shared decision contract with schema/model/calculation versions, unique run ID, data signature, expiry, failure state, and legacy adapters.
- SQLite prediction/outcome ledger with WAL mode, safe migrations, parameterized queries, retry handling, immutable run/horizon records, outcome settlement, and memory fallback.
- Strict completed-candle data-quality gate with PASS, PASS_WITH_WARNING, FAIL_MODEL, and FAIL_ALL behavior.
- Chronological purged walk-forward evaluation over settled out-of-sample ledger predictions, with at least six-row purge for the maximum horizon and one-row embargo.
- Out-of-sample probability calibration hierarchy with sigmoid/isotonic policies, chronological holdout diagnostics, Brier score, log loss, ECE, and reliability buckets.
- Dynamic horizon/regime/drift/quality/session/agreement/priority/actionability/EV thresholds with bounded fallbacks.
- Cost-aware expected value, conservative spread/slippage fallback, risk/reward, and break-even probability.
- Separate 1h/2h/3h/6h forecasts and reconciliation, prioritizing the existing 2–3 hour holding preference.
- Direction-preserving meta-label actionability gate that can approve the signal or force WAIT, never reverse it.
- Regime age, duration distribution, remaining duration, persistence, 1h/3h/6h transition risk, possible next regimes, Alpha, Delta, and Delta acceleration.
- Horizon-specific adaptive intervals with rolling residual coverage adjustment and conservative insufficient-history fallback.
- Prediction, feature, and decision drift statuses: STABLE, WATCH, DEGRADED, CRITICAL.
- Historical similarity evidence with weighted sample size and outcome consistency; it is explicitly not labeled as probability.
- NLP event-response memory with deduplication fields, normalized timestamps, 1h/2h/3h/6h outcomes, MFE/MAE, and Finnhub availability state.
- Auditable final policy requiring acceptable data quality, probability threshold, positive EV, actionability, interval quality, drift, regime conflict, and NLP conflict.
- Existing Lunch, PowerBI, Regime Summary, Backtest, Train Data, Engine, Pre-Original, Profile, exports, tables, histories, mobile layout, KNN, Greedy, Alpha/Delta, and original models were preserved.

## Important repairs

- Removed an active duplicate call that ran the complete Settings calculation twice.
- Added a session lock to prevent duplicate Streamlit rerun execution and duplicate ledger writes.
- Settings now opens Lunch only after a canonical result is successfully committed. FAIL_ALL remains on Settings with a concise diagnostic.
- Failed attempts preserve the previous valid canonical result and are recorded separately instead of silently presenting stale data as current.
- Replaced active normal-user raw traceback displays with concise safe messages while retaining log details.
- Restored the Finnhub API Connector directly inside the existing Research → NLP area.
- Extended NLP event-response horizons from 1/3/6 to 1/2/3/6 hours.
- Added aligned point/lower/upper horizon charting inside the existing PowerBI detail field to prevent array-length mismatch.

## Files added

- `core/decision_contract_20260617.py`
- `core/decision_product_engine_20260617.py`
- `core/prediction_ledger_20260617.py`
- `ui/decision_product_panel_20260617.py`
- `tests/test_decision_product_20260617.py`
- `DECISION_PRODUCT_UPGRADE_REPORT_20260617.md`

## Files modified

- `adx_dashpoard.py`
- `core/adx_shared_sync_20260615.py`
- `core/app/runner.py`
- `core/nlp_event_response.py`
- `core/settings_run_orchestrator_20260617.py`
- `tabs/antd_page_router_20260615.py`
- `tabs/final_lunch_upgrade_20260617.py`
- `tabs/other.py`
- `ui/nlp_research_panel.py`

## Test results

| Test | Result |
|---|---|
| Compile all Python files | PASS |
| Import `app`, `main`, and `adx_dashpoard` | PASS |
| Confirm real route registry and entry chain | PASS |
| 18 reliability unit tests | PASS |
| Canonical serialization and unique run IDs | PASS |
| SQLite ledger write/read and four horizon rows | PASS |
| Pending outcome settlement after due candles | PASS |
| Empty/malformed/duplicate/incomplete candle protection | PASS |
| Calibration and dynamic-threshold fallback behavior | PASS |
| Cost-aware EV and actionability fields | PASS |
| 1h/2h/3h/6h intervals and reconciliation | PASS |
| Regime transitions and drift statuses | PASS |
| Finnhub no-key and invalid-format behavior | PASS |
| Headless Streamlit startup and health endpoint | PASS |
| Streamlit AppTest initial authentication screen | PASS |
| Streamlit AppTest guest Settings page | PASS |
| Settings Run with no OHLC: FAIL_ALL, concise error, stays Settings | PASS |
| Settings Run with 130 completed synthetic H1 rows | PASS — canonical WAIT committed, original Lunch and PowerBI calculations ready, automatic Lunch navigation, 8.67 seconds |
| Research page shows NLP Finnhub connector without exception | PASS |
| Phone-mode button rerender | PASS |

## Dependency changes

No dependency file changes were required. The implementation uses Python standard-library SQLite and existing project dependencies (`pandas`, `numpy`, `scikit-learn`, `streamlit`, and `httpx`). `runtime.txt` remains Python 3.12.

## Unavoidable limitations

- Calibration, learned actionability, optimized thresholds, residual intervals, and performance-by-regime/session remain explicitly `INSUFFICIENT SAMPLE` or use marked conservative fallbacks until enough predictions have settled. No result is fabricated.
- Finnhub was tested for missing and invalid key handling, but a live valid-key request could not be tested because no user secret was available. The app remains fully operational without Finnhub.
- Streamlit Cloud local SQLite works during an app instance but may be reset by a redeploy or platform filesystem reset. The code includes safe creation/migration and memory fallback; durable cross-deploy history requires an external persistent volume/database, which was not added because paid services and new mandatory APIs were prohibited.
- Existing model internals that do not expose a standardized per-fold fit API are validated through their immutable settled out-of-sample ledger predictions using chronological purged windows rather than being silently retrained with replacement models.
- Spread and slippage use clearly marked conservative configurable fallbacks when broker-specific data is unavailable; expected value is an estimate, never guaranteed profit.
