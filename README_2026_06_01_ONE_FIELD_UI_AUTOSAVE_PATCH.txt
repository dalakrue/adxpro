ONE-FIELD UI + AUTOSAVE/DOWNLOAD-CENTER PATCH

Changes:
- Repeated top status/header/relationship cards are inside one collapsed field per tab.
- Open/close fields are smaller, lighter, more transparent Telegram-glass style.
- Profile inner choices use button-style tab choices instead of a selectbox.
- Database Center is inside Train Data and is read-only: no local Backup/Save/Download buttons.
- Downloads are centralized in the sidebar Download Center.
- Home, Train Data, Engine, Doo Prime, risk snapshots, deep Doo analysis, and database previews rely on auto-save/backend.
- Home duplicate main-tab launcher is collapsed to avoid duplicate sidebar/home tab buttons.
- Doo Prime refresh preserves open tab/inner section from previous patch.

Run:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8501
