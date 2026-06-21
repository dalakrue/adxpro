# Formulas and Assumptions

## SPIBB support rule

For confidence target `1-δ`, maximum allowed deviation `ε`, observed point-in-time support buckets `B`, and actions `A=3`:

`N_min = ceil((2 / ε²) * log((2 B A) / δ))`.

This is a conservative union-bound concentration threshold used to decide baseline bootstrapping. It is not presented as a full finite-MDP guarantee for financial markets.

## Off-policy estimators

Importance weight: `w_i = π_candidate(a_i|x_i) / π_behavior(a_i|x_i)`. Missing denominator or full candidate probability vector makes the estimator `NOT_IDENTIFIABLE`; probabilities are never inferred from scores or outcomes.

HCOPE reports unclipped `mean(w r)`, clipped/bounded `mean(min(w,c) clip(r,-R,R))`, ESS `(Σw)²/Σw²`, concentration `max(w)/Σw`, and a one-sided Hoeffding lower bound over the predeclared bounded range. Formal coverage requires bounded independent samples; serial dependence is not claimed away.

Doubly robust value: `mean[q(x,π) + w(r - q(x,a_behavior))]`. The nuisance model is fitted only on the earlier 60% chronological window and evaluated on the later 40%.

## Anchor regression

With anchor projection `P_A` and robustness parameter `γ`, the transformed objective uses `M = I + (sqrt(γ)-1)P_A` and fits least squares/ridge to `(MX, My)`. Reported robustness applies only to shifts spanned by pre-decision anchors. It is not causal discovery.

## Explicit-duration HSMM validator

Existing canonical regime labels are segmented chronologically. A bounded duration probability mass function uses Dirichlet smoothing. Given current age `a`, remaining-duration probabilities are conditioned on `D >= a`; hazard is `P(D=a | D>=a)`. No MCMC or render-time sampling is used.

## VaR, ES and Fissler–Ziegel score

Loss is negative settled net return. `VaR_α` is the empirical upper α-quantile and `ES_α` is the mean loss at/above that quantile. The FZ0-equivalent score is evaluated on returns `Y=-loss`, `q=-VaR`, `e=-ES`, with corrected action-domain checks `q >= e` and `e < 0`. It is a relative ranking score; absolute ES backtests are reported separately.

## CDaR

Equity is `E_t = Π_{i<=t}(1+r_i)` in settlement order. Drawdown is `D_t = max(0, 1-E_t/peak_t)`. `CDaR_α` is the mean of drawdowns at or above their α-quantile. Chronological order is never shuffled.

## Risk-constrained Kelly

The raw fractional Kelly approximation is `max(0, mean(r)/var(r))`, then bounded by the existing multiplier and hard user cap. For wealth floor `α_w` and maximum drawdown probability `β`, `λ=log(β)/log(α_w)` and candidate fraction `f` must satisfy `mean((1+f r)^(-λ)) <= 1`. CVaR/CDaR scales can only reduce the result. Any blocked safety state returns zero.

## Point-in-time boundary

All features, anchors, actions and probabilities must exist by `data_cutoff_timestamp`. Settlement occurs only at or after the fixed 1H, 2H, 3H or 6H target. Horizons are never selected after observing outcomes.
