FINAL PRIORITY / HISTORY / DATA VISUALIZATION FIX — 2026-06-11

Base: last working uploaded ZIP.

Added non-destructive patch:
- tabs/final_priority_history_dv_fix_20260611.py
- imported last in tabs/home.py

What changed:
1. Lunch priority ranking
   - Added display-only KNN + Greedy hourly priority board.
   - Priority scale is 1 to 14.
   - Labels:
     1-3 Best Opportunity
     4-6 Good Opportunity
     7-9 Watch / Wait
     10-12 Weak
     13-14 Avoid
   - Shows at least 2 best entry opportunity rows when history exists.
   - Ranking changes by hour using existing hourly rows only.
   - Original prediction logic is not changed.

2. Full Metric History controls
   - Added visible choice controls:
     Today, Last 2 Days, Last 5 Days, Last 10 Days, Last 25 Days,
     Custom Day, Custom Hour, NY/London Only, High Quality Only,
     BUY Only, SELL Only, WAIT Only, Best Entry Only, Worst Hour Only,
     Regime Change Only, Conflict Only, Pullback Allowed Only.
   - Added open/close filtered 25-day history table.
   - Added Backtest True/False, Correct Only, Wrong Only columns.

3. Data Visualization PowerBI projection
   - Added upper/lower 6H prediction band metrics.
   - Added st.metric:
     6H Average Predicted Price,
     6H Upper Bound Average,
     6H Lower Bound Average,
     Prediction vs Actual Close Error,
     Dynamic Projection Status.
   - Added extra choice buttons for projection view, band mode, replay filter, signal filter.
   - Kept existing PowerBI chart and ML tables.

4. Technical Logic section
   - Added Run Technical Logic Display button.
   - Section is hidden until clicked to prevent duplicate metric UI on open.
   - Uses latest Data Visualization / Lunch session data.
   - Valid fallback values avoid None / blank st.metric display.
   - Added Conflict Status and safer interpretation for direction mismatch.

5. 25-day history under expectation metrics
   - Added 25-day history under Next 1H Reasonable Expectation,
     Today Reasonable Expectation, and MTF Regime.
   - Added choices:
     Today, 2D, 5D, 10D, 25D, BUY, SELL, WAIT, Conflict, Correct Only, Wrong Only.

Compile check:
- python compileall passed for the full project.
