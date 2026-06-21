HOME COMMAND CENTER + ALL-TAB STATUS UPGRADE

What changed without removing original code:
1. Added tabs/home_split/home_command_center.py
   - Fast Home Command Center above the original Home launcher.
   - Data quality check: rows, source, last candle, median candle step, duplicate/missing close checks.
   - SAFE_DEMO warning so demo candles are not mistaken for live exit data.
   - Market pulse: 12H bias, regime, direction, DVE %, trust %, fat-tail context.
   - Account/margin pulse: margin level, stop-out gap, equity, free margin, floating P/L, position count.
   - Emergency Exit Guard: shows when EXIT BUY / EXIT SELL / HOLD-PAIR is safer.
   - Scenario table and full-side exit permission checks.
   - Compact copy/download report for GPT.

2. Updated tabs/home_split/implementation.py
   - Original Home launcher, Doo Prime, and Doo Prime Analysis remain.
   - New command center is inserted at the top of the Launcher tab.
   - If the new command center fails, the original Home tab still loads safely.

3. Updated core/app_shell.py
   - Shows a shared all-tab status bar before every tab.
   - Helps every tab see current symbol, timeframe, source, rows, last fetch, websocket status, and global pulse.

4. Updated core/system_upgrade.py
   - The global status bar no longer silently creates SAFE_DEMO candles.
   - Only explicit connector buttons load new market data.
   - This makes Home more correct for real trading/risk decisions.

5. Updated core/navigation.py
   - Sidebar Off button clears cached deep-analysis state too.

How to run:
1. Unzip this folder.
2. Open PowerShell inside quant_app_upgrade.
3. Run: pip install -r requirements.txt
4. Run: streamlit run adx_dashpoard.py

Important trading note:
- SAFE_DEMO means live connector failed and the app is showing synthetic/demo candles.
- Do not use SAFE_DEMO for real BUY/SELL exit decisions.
- The Home Command Center is a decision-support dashboard, not automatic execution.
