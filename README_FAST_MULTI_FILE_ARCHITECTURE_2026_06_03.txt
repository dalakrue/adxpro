FAST MULTI-FILE ARCHITECTURE UPGRADE - 2026-06-03
=====================================================

Goal
----
Refactor the project for faster file switching, easier future upgrades, and safer tab maintenance without changing the existing app behavior.

What changed
------------
1. Sidebar/navigation was split:
   - core/navigation.py is now a small compatibility facade.
   - core/navigation_parts/timer.py
   - core/navigation_parts/state.py
   - core/navigation_parts/connection.py
   - core/navigation_parts/panels.py
   - core/navigation_parts/main.py

2. Market data connectors were split:
   - core/connectors/data_connectors.py is now a small compatibility facade.
   - core/connectors/data_parts/utils.py
   - core/connectors/data_parts/fetchers.py
   - core/connectors/data_parts/session.py
   - core/connectors/data_parts/account.py

3. Large legacy files were preserved but isolated behind small facades.
   This keeps old imports working while making active edit files smaller and safer.

4. Files over 500 lines were moved into legacy_impl folders where possible.
   Active upgrade files are now mostly below 500 lines, so future UI/UX, engine,
   finder, and connector upgrades can be edited with lower risk.

5. Existing import paths are preserved.
   Example: from core.navigation import sidebar_nav still works.
   Example: from core.data_connectors import manual_connect still works.

How to run
----------
Use the same command as before:

python -m streamlit run main.py

or double-click RUN_APP_WINDOWS.bat.

Important note
--------------
No trading calculation logic was intentionally changed in this architecture patch.
This upgrade focuses on safer structure, faster maintenance, and easier future edits.
