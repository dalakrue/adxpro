UI/UX FULL UPGRADE - 2026-05-31

What was upgraded without removing original tab logic:

1) Universal header for every tab
- Shows current workspace/tab, symbol, timeframe, layout mode, source, rows, last candle, and refresh age.
- Shows LIVE / READY when shared dataframe is connected.

2) Safer data-quality warning
- If no shared dataframe is loaded, each tab clearly tells you to use sidebar Quick Refresh.
- If data is older than 30 minutes, it warns you before you rely on analytics.

3) Phone UI improvement
- Phone mode keeps Streamlit columns in compact grid layout.
- Metric cards are closer to square and easier to read.
- Wide tables scroll sideways instead of breaking the screen.
- Sidebar buttons renamed to Phone UI / Laptop UI for clarity.

4) Laptop UI improvement
- Better glass cards, clearer status badges, cleaner spacing, stronger visual hierarchy.
- Tabs, buttons, inputs, expanders, dataframes, metrics, alerts all have consistent styling.

5) Files added/changed
- Added: core/uiux.py
- Upgraded: core/app_shell.py
- Upgraded: core/styles.py
- Small label cleanup: core/navigation.py

Run:
streamlit run adx_dashpoard.py

If that entry point fails on your machine, use:
streamlit run main.py
