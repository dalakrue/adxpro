2026-06-02 Duplicate Metric + Open/Close Cleanup

What changed:
1. Removed repeated per-tab wrapper panels:
   - No more duplicate pro-tools expander on every tab.
   - No more repeated shared relationship expander on every tab.
   - No more repeated UI/background status expander on every tab.
   - Original tab logic is preserved below one compact page shell.

2. Home tab cleanup:
   - Home now renders only ONE Home Master open/close field.
   - Older Home Pro and Full Home dashboards are preserved in files but not rendered together because they repeated the same Source/Rows/Bias/Account metrics.
   - Bottom Home source and 12H safety status now use compact HTML cards instead of extra st.metric blocks.

3. Sidebar cleanup:
   - One-click console and maintenance panel now use compact cards instead of duplicate st.metric rows.
   - Connector, refresh, sync modeling, disconnect, timer, download center, websocket, and UI mode are preserved.

4. Train Data + Database cleanup:
   - Repeated global wrapper panels removed.
   - Important status metrics are now compact card rows.

5. CSS/UIUX:
   - Added core/ui/compact.py for reusable compact card helpers.
   - Added final duplicate-cleanup CSS layer for smaller glass metric cards and mobile-friendly grids.

Run:
    streamlit run main.py

If you need old hidden Home panels later, they are still preserved in:
    tabs/home_split/pro_home_dashboard.py
    tabs/home_split/home_full_upgrade.py

They are simply not rendered together by default to avoid duplicate visible metrics.
