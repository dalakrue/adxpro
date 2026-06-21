# Final Report — EURUSD H1 Production Promotion Guard

## What was inspected

- Full extracted package and runtime import chain from `app.py` through `adx_dashpoard.py`, `core.app_shell` and `core.app.runner`.
- The canonical shared calculation, Settings one-click transaction, atomic publisher and every direct canonical reader/session-key reference. See `CANONICAL_PUBLICATION_READER_AUDIT_20260621.csv`.
- All six existing Lunch fields and their lazy render paths.
- Full Metric and ten-decision history authority.
- Regime, reliability, KNN, Greedy, conflict, counter-trend, forecast, NLP and Power BI paths.
- Existing PBO, Deflated Sharpe, predictive-ability/SPA, online-FDR, conformal, BOCPD, ADWIN, MMD, Group-DRO, model-confidence-set, fixed-share, Model-X, provenance, metamorphic, CALM, CVaR-like and Kelly-like implementations.
- Existing research schemas, shadow modes, promotion controls, migrations, rollback patterns and all 35 test files.

## What was reused or upgraded

- Existing canonical BUY/SELL/WAIT engine remains the sole directional authority.
- Full Metric and ten-decision histories remain authoritative.
- Existing PBO, Deflated Sharpe, SPA/predictive-ability and online-FDR outputs are read as mandatory gates; module presence never counts as a pass.
- Existing regime labels and duration history are reused; the new HSMM component validates duration only.
- Existing CVaR-like/Kelly-like multiplier remains a stricter cap; the new risk layer can only reduce it.
- Existing SQLite bundle transaction and repository patterns are reused.

## What was added

- One consolidated `Production Promotion Guard`, called exactly once in the existing Run Calculation transaction.
- A prospective append-only policy decision ledger with fixed 1H/2H/3H/6H settlement.
- SPIBB support/bootstrap diagnostics; HCOPE; doubly robust OPE; anchor robustness; explicit-duration HSMM validation; joint VaR/ES scoring; ES backtesting; CVaR/CDaR; risk-constrained Kelly; and promotion-state registry.
- Seven additive idempotent tables, a standalone migration and backup-first rollback utility.
- Read-only cards and evidence tables inside existing Lunch Field 6.
- Governed risk configuration, duplicate-research audit, architecture/call-graph audit, formulas, paper mapping, model/data cards, tests, performance measurements, limitations and deployment instructions.

## What remained unchanged

- Existing formulas and canonical direction meaning.
- Existing Full Metric, ten-decision, regime, reliability, KNN, Greedy, conflict/counter-trend, forecast, NLP and Power BI logic.
- Existing six Lunch fields, tabs, pages, menu/navigation structure, copy functions, exports and JSON outputs.
- All original database files: four SQLite databases and one DuckDB file were restored byte-for-byte and verified by SHA-256 before packaging.

## Verification result

- **369 tests passed; 0 failed; 0 timed out across all 35 test files.**
- Dedicated new guard tests: 22 passed.
- Streamlit health endpoint: `ok`.
- Migration idempotency, copied-database integrity, deterministic rerun, atomic rollback and backup-first rollback tests passed.
- Performance measurements are in `artifacts/promotion_guard_performance_20260621.json`.

## Promotion-gate result

Software/resource/database mechanics pass their verified checks. Actual policy promotion remains blocked because the historical package has no valid behavior-action propensities or full candidate probability vectors, so overlap-aware HCOPE and doubly robust OPE are not identifiable. Prospective support, settled fixed-horizon evidence, tail calibration and all existing statistical gates have not all passed.

## Production influence statement

**Production influence was not promoted.**

The delivered state is fail-closed `SHADOW_NOT_PROMOTED` / `BLOCKED_INSUFFICIENT_EVIDENCE`. The guard cannot reverse BUY and SELL, cannot turn WAIT into a trade, cannot replace the canonical engine and cannot hide a failed gate. `FULL_RISK_PROMOTION` remains unavailable until every mandatory empirical, risk, QA and rollback gate passes in sequence.
