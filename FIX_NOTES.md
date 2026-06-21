# Fix Notes — Future-proof UI Shell

This upgrade isolates future UI/UX changes from trading logic by adding a small App Shell layer.

Important behavior:

- Main-page navigation does not rely on `st.expander`.
- The native sidebar starts collapsed and remains a backup only.
- Drawer state is stored in `st.session_state`.
- Menu item clicks set the active page and close the drawer automatically.
- JavaScript is optional only and never required for navigation.
- UI Health Check can report missing files, invalid active pages, export path issues, CSS load status, and duplicate literal widget keys.


## 2026-06-14 16:49:36 — Logic Safety Guard + Hidden Danger Engine
- Added additive logic-safety wrapper modules.
- Added hidden danger detector, no-trade guard, prediction drift monitor, regime age warning, conflict matrix, calibration, data quality guard, lookahead bias guard, signal stability, reason chain, shadow comparison, and audit table.
- Original calculations and display sources were not intentionally changed.
- Python compile check passed; ZIP integrity check passed after packaging.
- Heavy checks run only after Run Safety Check.

## 2026-06-14 — Sidebar Hard Fix
Problem fixed:
- Native sidebar could stay hidden after Guest/Login because an older hard-close patch injected force-hidden CSS.

Fix:
- Closing now uses optional JavaScript click attempts only.
- Force-hidden sidebar CSS is disabled by override.
- Main-page drawer contains a sidebar replacement panel, so API connection and timer remain available even if Streamlit's native sidebar fails.
- Native sidebar failure no longer blocks Home/Lunch from loading.
