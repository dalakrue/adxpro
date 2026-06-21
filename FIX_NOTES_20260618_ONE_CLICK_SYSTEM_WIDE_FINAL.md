# One-Click System-Wide Synchronization Final Fix — 2026-06-18

## Result

`Settings → Run Calculation + Open Lunch` is now the single calculation owner.
It calculates and publishes one canonical generation for Full Metric, Lunch,
Finder, Dinner, PowerBI, Regime standards/history, Research Data Analysis, Data
Mining, NLP, and AI grounding. After canonical publication, navigation opens
Lunch automatically. Active inner sections no longer require a second Run or
Load action.

## Main corrections

- Added `core/system_wide_completion_20260618.py` to publish all established
  cache aliases and a per-component readiness manifest in one transaction.
- Every active renderer reads the published generation. Missing components show
  the exact failed component and direct the user to `Settings → Errors / Fix
  Fast`; a completed generation never shows another generic Run request.
- The Settings run now builds all Research inner-tab packs, Data Mining and NLP
  in the same transaction.
- Finder is a read-only view of the canonical Lunch/Home priority table and does
  not recalculate prediction/history engines.
- Full Metric Regime History is restored inside Full Metric History and is
  published under the existing history aliases.
- Dinner is consolidated to two choices: `Regime + Combined Logic` and
  `AI Assistant`.
- PowerBI and Regime projection use the Settings-built cache; separate inner Run
  and Load buttons were removed.
- NLP uses a 10-day window, KNN/Greedy ranking, impact/protect fields, shared Data
  Mining outputs and visible connector errors. Manual NLP tools remain optional
  inside a collapsed expander.
- API secret inputs are owned by Settings. Drawer/sidebar/NLP surfaces show
  connection status only, preventing duplicate widget/key conflicts.
- AI prepared-question handling keeps the 1,000-question library but adds the
  exact selected pattern, category, answer rule and question-specific focus so
  different questions do not repeatedly return one generic answer.
- Copy Short is valid JSON capped at 4,000 characters and preserves current
  decision, next-1-hour TP context, next-6-hour TP context, less-risky 6-hour
  bias, regime, reliability, NLP rank 1 and top opportunities. Copy Full keeps
  the complete cached export.
- Phone rendering limits large displayed tables, wraps metric rows, keeps metric
  text visible, disables expensive motion/blur in low-heat mode and reduces the
  floating menu to approximately 124–148 px desktop and 128 px phone.
- Presentation cache clearing no longer deletes canonical calculation outputs.
- Operational errors are bounded, deduplicated, redacted and shown in Settings.

## Protected logic

`tabs/eurusd_h1_matrix.py` was not modified.

SHA-256:
`fe0797ab30f469f3ea748bc66a690b18a68aaf91306ac33c797bdcdcf6e60682`

No existing Full Metric formulas, thresholds, regime logic, Alpha/Delta logic,
KNN/Greedy scoring, PowerBI prediction formulas or central decision direction
were replaced.

## Validation performed

- Full-project Python bytecode compilation passed.
- 95 tests were collected.
- 85 non-causal regression tests were exercised by file; all completed tests
  passed.
- Nine causal/quant tests completed successfully. The final performance-heavy
  same-candle cache-invalidation test exceeded the local command time budget and
  produced no assertion failure before termination.
- New one-click synchronization tests verify object identity across aliases,
  readiness/error behavior, API-input ownership, Dinner consolidation, copy
  bounds, mobile low-heat CSS, AI question focus and the protected-file hash.
- Streamlit browser execution was not launched in this build container because
  the container does not have the `streamlit` package installed. The project
  requirements and entry point are preserved for its normal environment.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
