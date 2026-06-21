2026-06-09 FINAL MOBILE + HISTORY + POWERBI ML PATCH

What changed:
1. Full Metric Details + History now shows newest/current time first.
   - If current loaded data is 2026-06-09, tables start from 2026-06-09, not old 2026-05-15 rows.
   - Future data changes are handled automatically by sorting Date+Hour/time columns descending.

2. Separate 10-factor history also shows newest/current rows first.
   - Entry Strength, BUY Pressure, SELL Pressure, Hold Safety, Exit Risk, TP Quality, Pullback Readiness, Trend Capacity, M1 Confirmation, Master Decision.

3. EURUSD H1 matrix _history_table now returns descending/newest-first history.

4. Data Visualization tab keeps the original PowerBI + ML projection section and adds the main candlestick ML projection section:
   - actual candles
   - blue predicted future candles
   - light-blue current/latest candle prediction path
   - rolling last-10-continuous-day ML projection history
   - prediction-vs-actual error table
   - major regime estimate table

5. Mobile-first CSS patch added for iPhone use:
   - rounded buttons
   - compact metric cards
   - less horizontal padding
   - phone-safe dataframe containers

6. Heavy sections are still lazy:
   - Run Calculating first
   - Run Candlestick + ML Projection first
   - no forced heavy calculation on open

Validation:
- python compileall completed successfully in this package.
- tabs/home.py and tabs/eurusd_h1_matrix.py compile successfully.

Run:
streamlit run adx_dashpoard.py
