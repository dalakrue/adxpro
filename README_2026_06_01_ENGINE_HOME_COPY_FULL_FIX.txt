2026-06-01 ENGINE + HOME COPY FULL FIX

What was upgraded without deleting original code:

1) Home copy data button fixed stronger
- The existing browser copy button remains.
- Added native Streamlit fallback copy box under it.
- Added TXT download button for Home GPT export.
- This fixes browsers that block clipboard permission inside Streamlit iframe components.

2) Engine full upgrade layer added
- New shared-data Engine decision summary appears at the top of Engine.
- Uses the same st.session_state['last_df'] used by Home / Train Data / Pre Original.
- Adds quick metrics: status, rows, bias, safety %, ADX, pressure, 10-candle speed %, fat-tail z-score.
- Adds Engine GPT export with native copy box and TXT download.
- Original Engine inner tabs are not removed: Decision Engine, Prelive, Websocket Live, Backtest Original remain below.

3) Safer behavior
- Engine analysis catches errors safely and does not crash the app.
- N/A fat-tail values remain N/A and are not converted to zero.
- Export text tells GPT not to treat N/A as zero.

How to run:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8501

If port 8501 is busy:
streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8502
