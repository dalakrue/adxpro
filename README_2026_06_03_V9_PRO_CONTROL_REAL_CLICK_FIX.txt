V9 PRO CONTROL REAL CLICK FIX

What was fixed:
1. PRO CONTROL button no longer detects/clicks itself as the native Streamlit sidebar button.
2. First load is forced closed, so sidebar does not open by default.
3. PRO CONTROL stays fixed at top-left across tabs, scrolling, and reruns.
4. Open/Close works after the sidebar was manually closed, after tab changes, and on mobile.
5. Tab auto-close messages now sync with the PRO CONTROL state instead of fighting it.
6. Escape key closes sidebar. Backdrop closes sidebar on mobile.
7. UI remains additive only; trading logic, connectors, reversal system, and original tab code were not changed.

Main patched file:
- core/v7_sidebar_glass_control_patch.py
