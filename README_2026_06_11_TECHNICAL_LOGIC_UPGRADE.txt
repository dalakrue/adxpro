2026-06-11 Technical Logic Upgrade

Added as a non-destructive patch layer. Existing Lunch/Data Visualization/Finder renderers still run first.
No existing table, chart, ML table, Power BI history chart, copy button, or calculation function was deleted or renamed.

Added:
1. Regime vs Prediction Conflict Engine.
2. Multi-timeframe regime logic for H1, H4, and D1.
3. Forecast Agreement Score for LSTM, Transformer, XGBoost, and Prophet-style forecast paths.
4. Prediction Reliability History for previous predicted path vs actual over the last 2 days.
5. Probability Cone with blue future path, yellow previous prediction, upper band, and lower band.
6. Market Quality Score from 0 to 100.
7. Counter-trend label when regime direction and prediction direction disagree.
8. Reasonable expectation metrics for next 1H and today in Lunch and Data Visualization.
9. Finder sync wrapper mirrors latest Lunch/Data Visualization priority logic after calculation.
10. Manual-run behavior preserved: heavy projection calculations still run only after Run Calculating.
11. NY/London next-6-hour threshold logic from previous V6/V7 patch is preserved, including midnight rollover such as 21,22,23,00,01,02.

Main changed file:
- tabs/home_patch_20260609.py

Validation:
- python compileall passed for the project files in this ZIP.
