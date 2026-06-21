COPY-PASTE / RUN INSTRUCTIONS

1) Unzip this folder.
2) Open PowerShell inside quant_app_upgrade.
3) Install requirements:
   pip install -r requirements.txt
4) Run:
   streamlit run adx_dashpoard.py

What was upgraded without deleting original tab code:
- All tabs now show a shared system status card at the top.
- Sidebar has health status and snapshot save button.
- Websocket layer is safer and Twelve Data symbols are converted like XAUUSD -> XAU/USD.
- If live data is unavailable, app uses safe fallback/demo data instead of blanking/crashing.
- Existing Home, Engine, Train Data, Pre Original, and Profile tabs remain modular.

For Twelve Data websocket:
- Put your Twelve API key in Connector Settings.
- Open Websocket live feed.
- Provider = twelve.
- Click Start WS, then Consume WS ticks or wait for auto refresh.
