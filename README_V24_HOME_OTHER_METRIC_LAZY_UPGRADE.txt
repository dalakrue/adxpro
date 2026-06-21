V24 HOME / OTHER / METRIC LAZY UPGRADE

What changed
1. Sidebar is simplified to four parts only:
   - Home tab button
   - Other tab button
   - Connector Field open/close
   - Timer Field open/close

2. New top-level tab: Other
   - Engine, Train Data, Database, Pre Original, and Profile are now inner buttons under Other.
   - A Run Calculate button is placed before the inner buttons.
   - If Run Calculate is not pressed, those tabs do not render and do not auto-run.
   - Only the selected inner tab renders after Run Calculate is enabled. Hidden inner tabs remain lazy to reduce RAM.

3. EURUSD H1 Decision Matrix renamed to Metric
   - It is no longer a sidebar/top-level tab.
   - It is now inside Home as an inner button named Metric.
   - Metric has its own Run Calculate button.
   - If Run Calculate Metric is not pressed, Metric does not calculate or build heavy 25-day tables.

4. Metric 25-day history upgrade
   - Added one open/close section for 25D Separate History For All 10 Metric Decisions.
   - Each of the 10 decision factors is shown separately.
   - Tables are not mixed or combined.
   - Each table shows Scale /10 first and sorts newest/current H1 rows first.

5. Original calculation logic preserved
   - Existing Engine, Train Data, Database, Pre Original, Profile, Home, and Metric logic is still in place.
   - The upgrade mostly changes navigation, lazy-run gates, and the added separate 25-day Metric history tables.

Run
streamlit run main.py
