2026-06-10 V5 NY/London + Yellow 6H PowerBI Fix

What changed:
1. NY/London overlap section is now rendered directly above the two Copy buttons via the Lunch copy bar wrapper.
2. Start threshold hour and End threshold hour are now free sliders from 1 to 24.
3. NY/London overlap table now includes Decision column with exact states:
   - WAIT PULLBACK
   - HOLD
   - ALLOWED
   - NO TRADE
4. Added NY/London Alignment column and Risk Note column for EURUSD overlap-hour alignment.
5. NY/London overlap calculation remains manual-run only. It does not calculate automatically when the tab opens.
6. Candlestick PowerBI section now adds an extra Open/Close block:
   "Last Candle Predict Next 6 Hours Yellow Line"
7. Yellow projection block includes selectable future horizon 1-12 hours, projection choice, and risk filter.
8. The yellow line starts from the last actual candle close and projects the next hours, with upper/lower risk bands.
9. Kept previous last-2-day yellow prediction-vs-actual chart, so you can compare old prediction with actual candles.
10. Patch is runtime-safe: original functions remain preserved and only wrapper/extension functions are added.

Run:
streamlit run adx_dashpoard.py
