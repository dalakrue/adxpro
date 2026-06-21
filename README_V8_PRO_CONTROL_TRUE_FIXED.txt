V8 PRO CONTROL SIDEBAR TRUE FIX
================================

What was fixed:
1. The floating PRO CONTROL button now uses a stronger open/close system.
2. It first tries Streamlit's native sidebar open/close buttons.
3. If Streamlit's native selector changes or fails, it directly opens/closes the sidebar with CSS fallback.
4. It keeps the button fixed at the top-left of the app even after scrolling or switching tabs.
5. It restores sidebar open state after reruns/tab changes when PRO CONTROL is set to OPEN.
6. It adds a mobile glass backdrop; tapping the backdrop closes the sidebar.
7. It removes the old fake inside-sidebar PRO CONTROL label that looked like a button but did not open anything.
8. This is UI-only. Trading logic, connector logic, reversal logic, and account logic were not changed.

Main patched file:
- core/v7_sidebar_glass_control_patch.py

Run:
    cd new7
    streamlit run main.py

If port 8501 is already used:
    streamlit run main.py --server.port 8502
