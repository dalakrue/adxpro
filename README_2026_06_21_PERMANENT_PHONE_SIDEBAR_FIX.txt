PERMANENT PHONE SIDEBAR FIX — 2026-06-21

Problem
- Streamlit automatically discovered the root pages/ directory and displayed its
  native multipage sidebar on phone, covering most of the application.

Fix
- Preserved the old page wrappers under legacy_page_wrappers_disabled/ so
  Streamlit cannot auto-register them as sidebar pages.
- Added [client] showSidebarNavigation = false to .streamlit/config.toml.
- Added a permanent CSS/state policy covering the native sidebar, page navigation,
  collapsed/open button, overlay, and full-width main viewport on mobile.
- Removed every UI control that could unlock the native sidebar.
- Converted the old sidebar_nav compatibility function to state-only behavior.
- Kept the Main Page Menu as the single navigation and connection surface.

Run
- streamlit run app.py
