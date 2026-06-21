2026-06-01 ALERT + UI + DATABASE UPGRADE

What changed
1) Doo Prime one-hour sound alert rule added:
   - M1 DVE > 60
   - M1 Rising Efficiency > 35
   - M1 Falling Efficiency <= 3 (near zero)
   - H1 does not worsen
   - Margin Level >= 70%
   - If the same EXIT BUY or EXIT SELL candidate remains valid for 1 hour, the app plays a browser sound/vibration alert and saves the signal to data/doo_exit_alerts.csv.

2) Emergency matrix sound alert added:
   - If the emergency exit matrix outputs EXIT SELL, it plays an EXIT SELL sound.
   - If it outputs EXIT BUY, it plays an EXIT BUY sound.
   - The app records last EXIT BUY / EXIT SELL time and hides signals older than 21 hours.

3) Inner tab choices changed from radio style to sidebar-like tab buttons:
   - Home inner sections
   - Doo Prime inner sections
   - Doo Prime History choices
   - Deep Doo analysis frame choices
   - Train Data / Database Center choices

4) Database Center moved inside Train Data:
   - The Database main tab is removed from DEFAULT_TABS.
   - Open Train Data, then choose Database Center.

5) Sidebar download center added:
   - Sidebar -> Download center / auto-save database.
   - Tables are sorted by trading priority: emergency exits, Doo alerts, Doo account, training cache, market cache, engine/home/risk, then system tables.

6) Auto-save improved:
   - Doo account snapshots auto-save every 60 seconds when account data exists.
   - Emergency exit decisions auto-save every 60 seconds when rendered.
   - Deep Doo analysis snapshots auto-save after refresh.
   - Train data cache and training snapshots auto-save every 60 seconds when rows exist.
   - Home quant snapshots auto-save every 60 seconds when results exist.

7) UI/UX upgraded:
   - Telegram-glass style open/close fields.
   - Popup alert cards.
   - Glass animation / pop effect.
   - Long metric reasons moved under open/close fields so the screen stays clean.

Run
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8501

If port 8501 is busy, use:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8502
