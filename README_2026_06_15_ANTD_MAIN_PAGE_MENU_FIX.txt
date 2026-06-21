2026-06-15 Ant Design + Main-Page Menu Sidebar Fix

Goal
- Permanently avoid depending on Streamlit native sidebar open/close behavior.
- Make Ant Design navigation the primary menu with safe Streamlit fallback.
- Keep existing calculations, tables, charts, copy buttons, exports, JSON output, ML/KNN/Greedy, regime logic, AI Assistant, and PowerBI renderers unchanged.

Main changes
1. requirements.txt now includes:
   streamlit-antd-components>=0.3.2

2. Added ui/antd_navigation_20260615.py
   - Safe import:
     try import streamlit_antd_components as sac
   - safe_antd_navigation() uses sac.menu first.
   - If SAC is missing or fails, it falls back to st.radio / st.selectbox.
   - Fallback warning text:
     streamlit-antd-components not installed; using safe fallback navigation.
   - Uses st.session_state['active_page'] and st.session_state['active_subpage'] as the source of truth.
   - Main pages:
     Home, Lunch, Dinner, Morning, Data Visualization, Research, AI Assistant, Settings
   - Nested routes:
     Lunch: Full Metric Details + History, PowerBI Projection, Priority + Decision + Reliability, AI Assistant
     Dinner: Regime Summary, Combine Logic, AI Assistant
     Research: Data Mining, NLP, KNN / Greedy, Quant Structure

3. Added tabs/antd_page_router_20260615.py
   - Routes new top-level pages/subpages to existing renderers.
   - Does not change formulas, prediction engines, ML/regime/PowerBI calculations, or cached data builders.
   - Heavy original Data Visualization/PowerBI renderer remains run/load gated.

4. Main-page replacement menu
   - ui/main_menu_drawer.py now provides the stable expander:
     ☰ Open / Close — Main Page Menu
   - Contains navigation, nested navigation, timer, API/data connection status, symbol/timeframe controls, mobile controls, run calculation, reset UI state, and optional native-sidebar backup controls.

5. Native sidebar cleanup
   - ui/native_sidebar_js.py is now a no-JavaScript compatibility layer.
   - ui/sidebar_hard_lock.py is now a soft optional backup policy.
   - Fragile DOM click/querySelector sidebar open/close logic has been neutralized in the active style facade.
   - Native sidebar is not required for navigation.

Validation
- python -m compileall -q . passed.
- New/modified modules were import-tested with a lightweight Streamlit stub in the build sandbox.
- Full Streamlit runtime launch was not performed in the sandbox because Streamlit is not installed there.
