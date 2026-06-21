HOME MASTER UPGRADE - 2026-06-01

What changed:
1. Added tabs/home_split/home_master_upgrade.py as a non-destructive Home layer.
2. Home now opens with a Master Command Center before the old Home sections.
3. Added fast main-tab launcher buttons: Home, Engine, Train Data, Pre Original, Profile.
4. Added shared dataframe health score, source, symbol, timeframe, rows, and quality status.
5. Added mini market metrics: mini bias, last close, 10-candle move, 60-candle move, 120 return volatility, 120 range.
6. Added Doo Prime survival snapshot: margin level, stop-out gap, equity, margin, floating P/L, positions.
7. Added quick Refresh 600 and Refresh chosen bars buttons using the same sidebar connector state.
8. Added fast buttons to open Doo Prime and Doo Prime Analysis without duplicate connector conflict.
9. Added compact GPT copy text for Home/account/shared-data status.
10. Added snapshot save button to home_snapshots when database writer is available.
11. Added all-tab relationship map to verify Home/Engine/Train Data/Doo Prime/Profile shared-state connection.
12. Original Home, Home Pro, Full Home Control Center, Doo Prime, and Doo Prime Analysis remain available below.

Run:
streamlit run main.py --server.address 0.0.0.0 --server.port 8501

If port 8501 is already used, change only the number, for example:
streamlit run main.py --server.address 0.0.0.0 --server.port 8502
