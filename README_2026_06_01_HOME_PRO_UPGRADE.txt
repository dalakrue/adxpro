HOME PRO UPGRADE - 2026-06-01

What changed:
1. Added tabs/home_split/pro_home_dashboard.py as a non-destructive Home layer.
2. Home now opens with a fast control center first, while the original Home Command Center, Doo Prime, copy export, and analysis sections remain available below.
3. Added shared-data health status: source, symbol, timeframe, row count, quality, last candle.
4. Added fast market snapshot: mini BUY/SELL/WAIT bias, last close, 10-candle move, 60-candle move, 120-return volatility.
5. Added Doo Prime account survival snapshot when account data exists: margin level, stop-out gap, equity, margin, floating P/L, position count.
6. Added quick buttons: Fast Refresh 600, Refresh chosen bars, Open Engine, Open Doo Prime.
7. Added compact GPT copy export text area and latest candle preview.
8. Kept original code intact: the upgrade is additive and only changes Home show() to render the new dashboard above existing sections.

Run:
streamlit run main.py
or
streamlit run adx_dashpoard.py --server.port 8501
