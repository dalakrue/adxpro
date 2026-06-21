HOME FULL UPGRADE - 2026-06-01

What changed:
1. Added tabs/home_split/home_full_upgrade.py as a non-destructive Home enhancement layer.
2. Home now shows a visible Full Home Control Center before the original Home tools.
3. Added direct main-tab buttons: Home, Engine, Train Data, Pre Original, Profile.
4. Added fast shared refresh buttons:
   - Refresh 600 candles
   - Refresh chosen sidebar bars
   - Read Doo Prime/MT5 account
   - Clear UI cache without deleting market/account data
5. Added shared system health: source, symbol, timeframe, rows, data quality, last candle.
6. Added fast decision metrics: 12H bias, safety %, regime, direction, DVE %, trust %.
7. Added Doo Prime survival snapshot: margin level, stop-out gap, equity, margin, floating P/L, open positions.
8. Added compact candle preview and all-tab relationship map.
9. Original Home, Doo Prime, Doo Prime Analysis, copy export, and existing command center are preserved.

Run:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8501

If port 8501 is busy, use:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8502
