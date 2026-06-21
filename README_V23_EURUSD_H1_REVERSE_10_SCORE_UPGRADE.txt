V23 EURUSD H1 Decision Matrix Upgrade

What changed:
1. Upgraded tabs/eurusd_h1_matrix.py only. Original project structure and existing connectors remain intact.
2. Added reverse-style 10/10 score table:
   - Entry Strength /10
   - BUY Pressure /10
   - SELL Pressure /10
   - Hold Safety /10
   - Exit Risk /10
   - TP Quality /10
   - Pullback Readiness /10
   - Trend Capacity Remaining /10
   - M1 Confirmation /10
   - Master Decision /10
3. Added true last-25-day H1 hourly history table.
   - Every H1 candle gets its own score.
   - Search/filter by hour, for example 12:00 or 14:00.
   - Filter by minimum Master /10 score.
4. Added button-triggered calculation.
   - The tab does not calculate heavy 25-day history until you press Calculate / Refresh.
   - This reduces RAM and phone freezing in Streamlit.
5. Custom timeframe rule remains:
   - H1 is main dataframe.
   - M1 is confirmation only.
   - H1 and M1 are shown separately, not mixed.
6. Existing connector logic is not changed.

How to use:
1. Run Streamlit normally.
2. Select EURUSD.
3. Select H1 or CUSTOM timeframe.
4. Connect data.
5. Open EURUSD H1 Decision Matrix.
6. Press Calculate / Refresh EURUSD H1 Matrix.
7. Use 25D Hour History to search each hour score.
