MATH + ML ALGORITHM QUALITY UPGRADE - 2026-06-01

What changed:
1) Upgraded shared quant core:
   - core/models/quant_models.py is now the main upgraded algorithm file.
   - core/quant_models.py stays as compatibility wrapper, so old imports still work.

2) Stronger math quality:
   - safer OHLC cleaning, duplicate time handling, bad candle repair.
   - better ADX/DI/ATR fallback using EMA smoothing.
   - added log returns, ATR slope, realized volatility, robust tail z-score,
     noise ratio, pullback risk, breakout quality, and micro-structure score.

3) Stronger ML quality:
   - walk-forward chronological split to reduce look-ahead leakage.
   - unfinished future-label rows are excluded.
   - RandomForest + GradientBoosting + optional ExtraTrees ensemble.
   - validation accuracy calibration shrinks weak probabilities toward 50%.
   - safer fallback when scikit-learn or enough data is unavailable.

4) Better risk scoring:
   - quant_stack now combines ML confidence, historical match, Monte Carlo,
     ergodicity, fat-tail risk, exhaustion risk, noise risk, breakout quality,
     and account risk penalty.
   - Existing output keys are preserved: bias, safe_pct, scale10, regime,
     ml_conf_pct, history_match_pct, etc.

5) New diagnostics:
   - trend_math_snapshot(df) added for any tab to inspect algorithm status.
   - Train Data tab now includes “Math/ML Diagnostics”.

Validation:
- Python compile check passed for core, tabs, main.py, and adx_dashpoard.py.
- A sample OHLC dataframe successfully ran add_indicators, regime_label,
  ml_bias, quant_stack, and trend_math_snapshot.

Run:
streamlit run main.py
or
streamlit run adx_dashpoard.py
