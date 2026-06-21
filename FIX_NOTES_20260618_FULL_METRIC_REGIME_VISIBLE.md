# Full Metric History — Regime Inner Section Visibility Fix

## User requirement completed

The existing Regime inner section and its existing tables are now restored inside the active **Full Metric Detail + History** workspace and are not hidden behind a second Run button, nested expander, or inner tab.

## Files added or changed

- Added `ui/full_metric_regime_inner_renderer_20260618.py`
  - Reuses the already-published canonical regime result.
  - Reuses existing `regime_context_20260614` KNN/Greedy and Regime History tables.
  - Reuses persisted Full Metric/Major Regime history.
  - Falls back to existing regime-related columns from Full Metric History.
  - Performs display-only Alpha/Delta interpretation; it does not change formulas.
- Updated `ui/full_metric_shared_renderer_20260618.py`
  - Displays the existing Regime inner section directly after Complete Full Metric History.
- Updated `ui/lunch_restored.py`
  - Displays the same existing Regime inner section inside the restored original Lunch Full Metric History area.
- Added `tests/test_full_metric_regime_visibility_20260618.py`
  - Verifies existing values/tables are reused.
  - Verifies both active Full Metric paths render the section.
  - Verifies the restored renderer has no nested expander, button, or hidden tab.

## Protection confirmation

`tabs/eurusd_h1_matrix.py` was not modified. Its SHA-256 remains:

`fe0797ab30f469f3ea748bc66a690b18a68aaf91306ac33c797bdcdcf6e60682`

No Full Metric History, Regime, Alpha, Delta, KNN, Greedy, NLP, Power BI, reliability, conflict, or model formula was changed.

## Validation executed

- `python -m compileall -q .` — PASS
- `pytest -q` — 67 passed
- `python tools/validate_architecture.py` — PASS
- `python tools/validate_final_sync_20260617.py` — PASS
- `python tools/validate_finnhub_nlp_restore_20260617.py` — PASS

Preferred entry file: `app.py`

Run command:

```bash
streamlit run app.py
```
