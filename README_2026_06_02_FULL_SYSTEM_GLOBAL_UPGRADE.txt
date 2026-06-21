2026-06-02 FULL SYSTEM GLOBAL UPGRADE

WHAT WAS UPGRADED
1. Added core/global_upgrade.py as a safe additive layer.
   - Does not delete original Home / Engine / Train Data / Database / Profile logic.
   - Adds shared command center to each main tab.
   - Adds copy button that copies JSON snapshot: source, symbol, timeframe, data quality, market bias, account margin, positions, and last 5 candles.
   - Adds session repair button to recover missing/corrupted session keys.
   - Adds data-quality scoring: missing columns, duplicate candles, large gaps, bad OHLC values.
   - Adds quick mini-bias from current shared dataframe.

2. Home tab upgraded.
   - New command center appears at top.
   - Copy all shared data works from Home.
   - Original Home implementation remains unchanged behind wrapper.

3. Sidebar upgraded.
   - New Full-system quick actions expander.
   - Sidebar copy button copies the same full shared snapshot.
   - Session repair button added.
   - Existing timer, connector, download center, websocket, relation hub remain preserved.

4. Engine tab upgraded.
   - New Engine command center at top.
   - Original engine, prelive, websocket, and decision modules remain preserved.

5. Train Data tab upgraded.
   - New Train Data command center at top.
   - Existing incremental training/validation/database sections remain preserved.

6. Database tab upgraded.
   - New Database command center at top.
   - Database remains read-only; download/export stays centralized in sidebar.

7. Profile tab upgraded.
   - New Profile command center at top.
   - Original profile dashboard remains preserved.

8. CSS / UIUX / background effect upgraded.
   - Added extra soft ocean glass animation layer.
   - More compact chips, metric glow, better expander/dataframe rounding.
   - This is additive and loaded after original CSS.

FILES CHANGED / ADDED
- ADDED: core/global_upgrade.py
- UPDATED: core/app/runner.py
- UPDATED: core/navigation.py
- UPDATED: tabs/home.py
- UPDATED: tabs/engine.py
- UPDATED: tabs/train_data.py
- UPDATED: tabs/database_tab.py
- UPDATED: tabs/profile.py

HOW TO RUN
1. Unzip this project.
2. Open PowerShell in the project folder containing main.py.
3. Run:
   pip install -r requirements.txt
   streamlit run main.py --server.address 0.0.0.0 --server.port 8501

IMPORTANT
- MT5/Doo Prime still requires local MetaTrader 5 open and logged in.
- Streamlit Cloud cannot run MetaTrader5 directly; use TwelveData or Doo Bridge on VPS for live broker data.
- This upgrade is additive and designed to avoid breaking original code.
