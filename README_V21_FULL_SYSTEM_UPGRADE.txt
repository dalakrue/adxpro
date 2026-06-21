V21 FULL SYSTEM UPGRADE - COPY/PASTE ZIP READY
================================================

What changed without removing original code:

1) Added core/full_system_upgrade.py
   - Shared dataframe helper
   - OHLC normalization helper
   - System health model
   - V21 glass CSS/background animation/popup layer
   - Home TP/range helper
   - Engine decision guardrail helper
   - Train Data incremental readiness checker
   - Database safety notes
   - Profile runtime overview
   - Sidebar Copy All Data JSON fallback

2) Updated core/app/runner.py
   - Loads V21 UIUX CSS after the existing CSS stack
   - Renders V21 popup messages safely
   - Keeps original app lifecycle and tab loading unchanged

3) Updated core/navigation_parts/main.py
   - Added V21 sidebar control status
   - Added Train Data and Database icons in sidebar
   - Added Copy All Data JSON fallback inside sidebar controls
   - Added popup feedback after quick refresh

4) Updated core/config/defaults.py
   - Sidebar now includes:
     Home, Engine, Train Data, Database, Pre Original, Profile

5) Updated tab wrappers
   - Home: extra TP/range/data health panel before original Home logic
   - Engine: extra guardrail panel before original Engine logic
   - Train Data: extra incremental training readiness panel before original logic
   - Database: extra safety/status panel before original read-only DB logic
   - Profile: extra runtime/system health panel before original logic

Run:
    streamlit run main.py

If main.py has an issue, run:
    streamlit run adx_dashpoard.py

Note:
This patch is non-destructive. Original implementation imports and tab logic are still preserved below the new V21 panels.
