KNN PRIORITY PLACEMENT UPGRADE - 2026-06-11

This upgrade is additive only and uses the last working ZIP as base.

Added:
1. KNN Priority Score 0-100 using existing stored/display metrics only.
2. Priority Label: A+, A, B, C, Avoid.
3. Important Fact Board at the top of Lunch and Data Visualization wrappers.
4. Placement controls:
   - Sort by KNN Priority
   - Sort by Reliability
   - Sort by Market Quality
   - Sort by Exit Risk
   - Show A+ Only
   - Show Avoid Only
   - Show Conflict Only
   - Show Counter Trend Only
5. KNN priority columns are added non-destructively to metric/history/regime/overlap/backtest/finder-style tables when those tables are displayed.
6. KNN Priority Cards are added above priority views.
7. Phone-safe behavior: no auto heavy calculation, no new ML model, no new prediction engine, uses existing stored/session rows only.

Files changed:
- tabs/home.py
- tabs/knn_priority_placement_20260611.py
- README_2026_06_11_KNN_PRIORITY_PLACEMENT.txt

Validation:
- Python compile check passed for all .py files in the project.
- Runtime Streamlit import was not run in this sandbox because Streamlit is not installed here; the app already includes Streamlit in requirements.txt for deployment.
