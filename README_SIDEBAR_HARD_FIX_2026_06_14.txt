SIDEBAR HARD FIX 2026-06-14

Goal:
- Native Streamlit sidebar can be opened/closed again after guest/login.
- No old force-hidden CSS is allowed to permanently hide the sidebar.
- Main-page drawer now includes critical sidebar functions, so the app works even if the native sidebar cannot open.

Changed display/control layer only:
- ui/native_sidebar_js.py: optional JS open/close/toggle helpers.
- ui/sidebar_fallback_panel.py: main-page replacement controls for API/data connection, timer, UI mode, and account logout.
- ui/main_menu_drawer.py: drawer now shows native sidebar JS buttons and the fallback control panel.
- core/ui/styles.py: overrides old force-hide sidebar behavior.
- core/app/runner.py: native sidebar errors no longer stop the app.

Protected:
- Existing trading calculations, prediction logic, ML tables, regime logic, safety engine, copy/export logic, and tab sources were not intentionally changed.

Validation:
- Python compile check passed.
- ZIP integrity check passed.
