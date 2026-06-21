2026-06-12 Sidebar Native Stability Fix

What changed:
- Removed the active JavaScript DOM sidebar force-close behavior.
- Kept Streamlit's native sidebar open/close control responsible for real sidebar state.
- Added a CSS-only sidebar stability patch so old force-closed classes cannot keep the sidebar invisible.
- Added one stable main-page Menu / Close expander panel for navigation fallback.
- Softened sidebar border, shadow, spacing, and mobile button touch size.
- Removed the AI Assistant Lite direct sidebar DOM close script.
- Kept existing tabs, calculations, metrics, tables, charts, copy buttons, exports, AI Assistant, and logic.

Files changed:
- core/ui/styles.py
- core/app/runner.py
- core/navigation_parts/main.py
- core/galileo_theme_20260612.py
- core/sidebar_stability_20260612.py
- tabs/ai_assistant_lite.py

Important behavior:
- Native Streamlit sidebar open/close is not overridden by custom JavaScript anymore.
- If the sidebar is closed or hard to open on iPhone, use the main-page "Open / Close — Main Page Menu" expander.
- request_close_sidebar() is preserved for compatibility but no longer hides/clicks private Streamlit DOM.
