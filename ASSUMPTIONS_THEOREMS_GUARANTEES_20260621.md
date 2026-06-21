# Assumptions, Theorems, and Guarantee Boundaries

## General distinction

This package implements mechanisms inspired by ten papers. A mechanism being present is not the same as its theorem assumptions being satisfied. Results are labeled SHADOW, INSUFFICIENT_EVIDENCE, or BLOCKED unless evidence and assumptions are explicit.

## 1. Model-X knockoffs

**Implemented:** deterministic second-order Gaussian equi-correlated knockoff construction, knockoff+ style threshold, feature statistics, target FDR configuration, two chronological windows, and regime stability review.

**Required for exact theorem-level control:** valid exchangeability/conditional construction for the true covariate distribution and valid response-free knockoff generation. Those conditions are not proven for dependent EURUSD time-series features. Therefore `fdr_control_claimed = false`; results are review evidence only.

## 2. Online FDR

**Implemented:** one ordered controller, deterministic version migration/reset, bounded recent test identities, allocated alpha, wealth accounting, and family/source records.

**Guarantee boundary:** theorem-level FDR/FDP control depends on valid null p-values and the dependence conditions of the selected online rule. The controller documents these assumptions and does not claim production control without validation of every contributing test family.

## 3. Reject option

**Implemented:** a documented rejection cost, risk estimate, coverage, WAIT rate, accepted-decision risk, and missed-opportunity rate.

**Safety guarantee enforced by code:** no direct BUY↔SELL reversal and no WAIT promotion. This is a software invariant, not a claim of optimal rejection cost.

## 4. Flexible asymmetric loss

**Implemented:** fixed versioned weights for wrong direction, TP-late proxy, SL-first proxy, maximum adverse excursion, interval miss, and high-exit-risk proxy.

**Limitation:** the existing settled ledger records touches but not exact intrahour first-touch order, so TP-late/SL-first are conservative proxies. Weights are not tuned on the complete history.

## 5. SHAP / contribution explanations

**Implemented:** routing to existing TreeSHAP payloads for compatible trees, exact existing linear contributions, and grouped deterministic-rule contributions.

**Guarantee boundary:** attribution decomposes an output; it is not causal identification. No causal claim is displayed or stored.

## 6. Monotonic calibrated lookup concepts

**Implemented:** six empirical monotonicity contracts with binned violation rates.

**Guarantee boundary:** this is a validator, not a constrained production model. Protected scores are not modified. Sparse support can only produce INSUFFICIENT_EVIDENCE.

## 7. Higher-order delta processing

**Implemented:** exact append-safe count, sum, sum of squares, min, max, and contingency counts; means/variances derive from sufficient statistics.

**Software guarantee:** candidate delta state is compared against full recomputation with strict numerical tolerance. A mismatch changes mode to `REJECTED_DELTA_MISMATCH` and publishes exact recomputation instead. Exact quantiles, Matrix Profile, DTW ranks, knockoff selection, and latest/top-k remain full/coordinated recomputations.

## 8. Provenance semirings

**Implemented:** compact immutable node and edge identities; union/alternative evidence corresponds to addition and joint dependency to multiplication at the interpretation level.

**Guarantee boundary:** the system stores a bounded lineage graph, not arbitrary symbolic polynomials. It explains source dependencies but does not prove causal provenance.

## 9. Metamorphic testing

**Implemented:** 12 required relations. A PASS demonstrates the coded relation on tested inputs; it does not prove correctness for all possible market data.

## 10. CALM

**Implemented:** operation classification and coordination boundary documentation.

**Software guarantee:** non-monotonic latest/current/top-k/controller/pointer updates are not exposed until the canonical SQLite transaction commits. Append-only settled evidence and lineage facts can be accumulated without retracting prior facts.

## Promotion rule

A future technique may influence production only after all required gates pass in at least two independent chronological windows, no catastrophic regime failure occurs, calibration/resource/monotonic/metamorphic gates pass, and a separately reviewed promotion flag is enabled. This delivery intentionally leaves that flag off.
