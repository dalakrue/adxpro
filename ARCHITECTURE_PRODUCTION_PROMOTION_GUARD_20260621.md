# Architecture — Production Promotion Guard

## Traced runtime

```mermaid
flowchart TD
  A[app.py] --> B[adx_dashpoard.py]
  B --> C[core.app_shell]
  C --> D[core.app.runner]
  D --> E[Settings / menu Run Calculation]
  E --> F[core.settings_run_orchestrator_20260617.run_settings_calculation]
  F --> G[core.adx_shared_sync_20260615.ensure_shared_calculation_result]
  G --> H[Existing canonical engine and protected Full Metric / regime / reliability / KNN / Greedy / forecast / NLP / Power BI outputs]
  H --> I[Existing research calibration, risk stack, history, regime trust, validation and prior ten-paper shadow layers]
  I --> J[production_promotion_guard_20260621 — exactly once]
  J --> K[Pre-publication canonical validation]
  K --> L[canonical_runtime_20260617.publish_canonical_atomically]
  L --> M[services.canonical_snapshot_store.commit_snapshot — BEGIN IMMEDIATE]
  M --> N[Canonical snapshot + all additive evidence tables]
  N --> O[operational_sync_20260618]
  O --> P[Lunch / Dinner / Finder / Research / AI / Power BI read-only consumers]
  N --> Q[Lunch Field 6 latest committed guard cards and bounded evidence tables]
```

## Protected authorities

- Sole directional authority: the existing canonical decision engine.
- Shared calculation: `core/adx_shared_sync_20260615.py::ensure_shared_calculation_result`.
- One-click transaction: `core/settings_run_orchestrator_20260617.py::run_settings_calculation`.
- Atomic publisher: `core/canonical_runtime_20260617.py::publish_canonical_atomically` and `services/canonical_snapshot_store.py::commit_snapshot`.
- Full Metric and ten-decision display authority: Lunch Field 1 in `ui/lunch_four_core_fields_20260619.py` and its existing shared renderers/history stores.
- The guard receives a deep copy of completed canonical outputs and publishes no action/direction key.

## Six existing Lunch fields preserved

1. Full Metric 25-Day History + Decision Tables.
2. Power BI Price Prediction Path.
3. 25-Day Regime History + Lower / Medium / Higher Standards.
4. Dinner Full Combined Intelligence.
5. Grounded AI Assistant.
6. Future Strategy Research History, now containing concise guard cards and detailed read-only evidence.

## One consolidated guard

`production_promotion_guard_20260621.py` orchestrates the ledger, SPIBB/HCOPE/DR, anchor robustness, HSMM duration validation, VaR/ES/CVaR/CDaR, constrained sizing and promotion registry. These are validators and risk gates, not ten decision engines.
