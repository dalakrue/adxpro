M1 ADX Quant Pro — all-tabs fixed upgrade

Run on Windows:
1) Extract this zip.
2) Open PowerShell inside the quant_app_upgrade folder.
3) Install requirements if needed:
   pip install -r requirements.txt
4) Run:
   streamlit run adx_dashpoard.py

Alternative:
   streamlit run main.py

What was fixed/upgraded:
- Removed duplicate st.set_page_config risk from the entry file.
- Added main.py as a safe alternative launcher.
- Added RUN_APP_WINDOWS.bat for one-click local/Tailscale running.
- Added global status bar before every tab.
- Added Global Market Pulse for every tab without replacing original tab logic.
- Kept original modules and wrappers intact.
- Websocket panel remains optional; normal MT5/Twelve/Doo Bridge connectors still work if websocket fails.

Important:
- Use sidebar connector once. All tabs read st.session_state['last_df'].
- For fast refresh use 600 candles. Use 60000 only for deep analysis because it can be slow.
