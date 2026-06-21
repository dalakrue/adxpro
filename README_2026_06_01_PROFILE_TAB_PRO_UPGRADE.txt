PROFILE TAB PRO UPGRADE - 2026-06-01

What changed without breaking original code:

1) Profile tab remains routed through tabs/profile.py, so old imports still work.
2) Fixed compatibility wrapper inside tabs/profile_dashboard_split/profile.py.
3) Added safer dataframe health summary helper:
   - row count
   - column count
   - missing percentage
   - duplicate row count
   - latest timestamp detection
4) Upgraded Profile Overview into a stronger command center:
   - live rows
   - latest price
   - equity / balance / floating P/L / margin level
   - source / symbol / timeframe
   - profile decision state: READY or CAUTION
   - reason list explaining why Profile is ready or risky
5) Upgraded Data Health:
   - compact metrics for live dataframe quality
   - missing data percentage
   - duplicate row detection
   - latest timestamp display
6) Upgraded Settings:
   - better organized two-column controls
   - trade journal auto-save toggle
   - min margin level setting
   - manual Save Settings Snapshot Now button
   - existing 60-second auto-save preserved
7) Kept sidebar connector system unchanged.
8) Kept Home, Engine, Train Data, Pre Original and Profile routing unchanged.
9) Kept original CSV/database functions unchanged.
10) Added safe fallbacks, so one Profile inner section crash will not break the full app.

Run:
streamlit run main.py

If main.py does not work in your folder, run:
streamlit run adx_dashpoard.py
