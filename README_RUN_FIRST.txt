QURANT7 FIXED READY - M2 SIMILAR DAY VERSION

Run:
  cd qurant7/quant_app_upgrade
  pip install -r requirements.txt
  streamlit run adx_dashpoard.py

What changed in this version:
- Main Backtest tab is now a fast M2 last-120 similar-day finder, not a strategy backtest.
- It compares today's latest 120 M2 candles with older 120-candle M2 regions.
- It searches up to the last 100 days and excludes today + yesterday when timestamps are available.
- It ranks similar days and shows next-120-M2 context only for regime guidance.
- You can enter multiple symbols separated by comma, such as XAUUSD,EURUSD,GBPUSD.
- Original Pre is now an independent sidebar tab: Pre Original.
- Original Backtest is now an independent sidebar tab: Backtest Original.
- Doo Prime page is upgraded with real MT5 account stats, risk status, exposure, and history.
- Risk is only under Home > Doo Prime; duplicate risk saving on every refresh was removed.
- Engine dashboard now shows one efficient threshold table and Good/Bad/Very Good/Dangerous labels.

Notes:
- MetaTrader5 works only on supported local Windows/MT5 setups.
- If MT5/Twelve data is unavailable, the app uses safe demo data so the dashboard does not crash.
- For real M2 100-day search, open MT5, log in to Doo Prime, then use MT5 M2/Backtest buttons.
