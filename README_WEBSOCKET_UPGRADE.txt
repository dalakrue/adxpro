WEBSOCKET UPGRADE

This ZIP adds an optional websocket live-feed layer without removing your original code.

How to use:
1. Install requirements:
   pip install -r requirements.txt

2. Run the app:
   streamlit run adx_dashpoard.py

3. Open the sidebar > 🌐 Websocket live feed.
   - provider=generic: paste your own ws:// or wss:// feed URL.
   - provider=twelve: enter your Twelve Data API key in Connector settings, then start WS.

4. Press Start WS, wait a few seconds, then press Consume WS ticks.
   The ticks are converted into candles and merged into st.session_state['last_df'].
   All tabs use the same shared dataframe.

Expected incoming generic JSON examples:
{"symbol":"XAUUSD","price":2350.12,"time":"2026-05-30T12:00:00"}
{"symbol":"XAUUSD","bid":2350.10,"ask":2350.14,"timestamp":1780123456}

Safety:
- If websocket disconnects, original MT5/Twelve/Doo Bridge/manual refresh remains available.
- No original tab function was deleted.
