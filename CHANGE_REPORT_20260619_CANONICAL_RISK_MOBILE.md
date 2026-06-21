# Change Report — Canonical Risk, Finder, Train Data and Mobile Upgrade

## Implemented

- Added frozen, checksumed canonical `RunSnapshot` publication.
- Added atomic SQLite snapshot commit with rollback preservation.
- Added run/generation verification and stale-alias repair.
- Added display-only EURUSD position sizing with aggregate scale-in risk, minimum-lot SKIP, margin calculation and SAFE/CAUTION/BLOCK status.
- Added Lunch top risk/status metrics, priority-based disclosure defaults and generation-scoped manual controls.
- Added current-generation Copy Short, Copy All and JSON export controls.
- Replaced Finder calculation behavior with canonical, paginated, database-filtered presentation.
- Added Train Data identity, quality metadata and bounded preview without automatic retraining.
- Consolidated the active sidebar/menu path; native sidebar is fallback-only.
- Added mobile 44-pixel touch targets, one-column metric behavior and bounded table rendering.
- Added dependency groups and isolated optional heavy packages.
- Added performance tracing and canonical snapshot storage services.
- Re-expressed one existing next-candle research target with explicit positional alignment. The mathematical formula and output are unchanged; the last row remains unlabeled.

## Protected logic preserved

No trading formula, forecast formula, Full Metric History calculation, regime calculation, priority calculation, KNN/Greedy calculation, Power BI projection, NLP result, ML result or BUY/SELL/WAIT rule was replaced, weakened or recalculated by the new services.

The following categories remain authoritative and unmodified numerically:

- Full Metric History and reverse-decision metrics
- Master, Entry, Hold, TP and Exit Risk scores
- Regime and forecast calculations
- Reliability and priority calculations
- KNN and Greedy ranking logic
- Power BI Prediction Projection
- Existing ML/NLP calculation outputs
- Existing Run Calculation ownership

## Run command

```powershell
streamlit run app.py
```
