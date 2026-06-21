2026-06-11 Finder Alignment Upgrade

Base: uploaded last working ZIP.
Non-destructive rule followed: no existing table, chart, ML table, history chart, copy button, tab, function, or calculation was deleted/renamed/removed.

Added:
1. Finder Alignment Engine wrapper after the existing Finder renderer.
2. Day selector + hour selector.
3. Run Finder Calculation button so heavy Finder calculations do not auto-run on open.
4. Dynamic Priority #1/#2/#3 st.metric ranking.
5. Exact selected-hour table with Master Score, Entry Score, Hold Safety, Exit Risk, TP Quality, Regime, Prediction Direction, Market Quality, Forecast Agreement, Reliability, Conflict Status.
6. Next 1H Reasonable Expectation and Today Reasonable Expectation st.metric cards.
7. Finder Replay table for last 2 days: previous predicted path vs actual, prediction error %, direction correct/wrong.
8. Probability cone with blue future path, yellow previous path, upper band, lower band.
9. EURUSD H1 Alignment Score 0-100 using H1/H4/D1-style regime proxies, Forecast Agreement, Market Quality, Reliability, and Conflict Engine.
10. Finder Decision Engine final table: Regime Direction, Prediction Direction, Conflict, Counter-Trend Label, Reliability, Market Quality, Final Decision.
11. Final Decision options limited to: ALLOWED, WAIT PULLBACK, HOLD / PROTECT, NO TRADE.

Mobile/RAM/CPU notes:
- The new Finder layer only calculates after clicking Run Finder Calculation.
- It reuses already-loaded candles/results/session data when available.
- It falls back safely if data is missing instead of crashing the page.
- Existing Lunch, Data Visualization, Power BI unified view, ML tables, Power BI history charts, and NY/London midnight logic remain untouched.

Files changed/added:
- Added: tabs/finder_alignment_upgrade_20260611.py
- Modified: tabs/home.py to install the new patch after existing patches.
