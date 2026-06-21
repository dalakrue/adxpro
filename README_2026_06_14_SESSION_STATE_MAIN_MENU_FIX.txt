2026-06-14 SESSION-STATE MAIN PAGE MENU FIX

Changed only the display/control layer for navigation stability.

What was fixed:
- Replaced the old "☰ Open / Close — Main Page Menu" st.expander fallback with a session_state-controlled main-page drawer.
- Added one Menu / Close toggle button only.
- Drawer menu item clicks set tab_choice, mark fast navigation, automatically close the drawer, and request a safe native sidebar close/hide fallback.
- Native Streamlit sidebar now starts collapsed through st.set_page_config(initial_sidebar_state="collapsed").
- Native sidebar remains available as a backup control panel; main-page drawer does not depend on it.
- Added mobile-friendly drawer CSS: rounded card, soft shadow, large tappable buttons, tighter iPhone spacing.

Safety notes:
- No prediction logic, calculation, table, chart, copy button, export, JSON output, ML table, history table, tab source, function, or section source was intentionally deleted or simplified.
- Python compile check was run with: python3 -m compileall -q .
- ZIP integrity should be checked after packaging with: unzip -t <zipfile>
