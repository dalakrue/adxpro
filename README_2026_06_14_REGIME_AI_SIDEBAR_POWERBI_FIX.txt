2026-06-14 Regime Priority + AI Classification + Sidebar Hard Close + PowerBI Visual Path Fix

Base: uploaded last working ZIP.

Applied as additive patches:
- tabs/home_regime_inner_tab_20260614.py
- tabs/home.py final import hook
- tabs/ai_assistant_lite.py compact one-input NLP/autocomplete patch
- core/ui/styles.py hard sidebar close + low-CPU/low-RAM CSS patch
- core/sidebar_stability_20260612.py close/allow-sidebar controls in stable main menu
- core/navigation_parts/connection.py sidebar close after Connect/Refresh
- tabs/final_research_projection_auth_sync_20260612.py display-smoothed red synced PowerBI path

What changed:
1. Home inner tab now includes Regime.
2. Regime tab consolidates regime metrics, confidence, conflict, priority, acceleration, rising/falling efficiency, efficiency, accuracy score, reliability score, forecast, prediction, KNN/Greedy regime priority, and regime history data table.
3. AI Assistant now keeps one combined input box. Bottom chat_input was removed to prevent duplicate input fields.
4. AI suggestions now appear as shadow KNN/Greedy priority rows below the input. Typing en/entry/tp/regime/risk/prediction surfaces related patterns.
5. Added 1000 lightweight local question patterns to the existing NLP pattern list. This is data only, not a model.
6. Local NLP recognition is now inside an Open / Close expander to reduce clutter.
7. Question selectbox remains only inside the Open / Close Question Box expander.
8. Sidebar close now uses session-state CSS force hide plus JavaScript retry attempts. Stable main menu has Close Sidebar and Allow Sidebar Again.
9. Connect/Refresh and Home inner-tab button clicks request sidebar close.
10. Red PowerBI synced path is visually smoothed with interpolation/spline while exact forecast points and underlying prediction data remain unchanged.
11. CSS/UI spacing and shadows are reduced for iPhone 11 Pro RAM/CPU.

Critical rules respected:
- No new prediction engine.
- No new ML model.
- No external API.
- Existing calculations/prediction data are not changed.
- New regime table calculations run after Run Regime Sync.
- Existing sections remain available.

Validation:
- py_compile passed for patched files.
- Full compileall passed.
- ZIP integrity test passed.
