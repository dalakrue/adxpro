ADX Quant Pro — Sidebar Connector + Train Data Upgrade

What changed:
1. One global API connector now lives in the sidebar.
   - Choose fallback / mt5 / twelve / doo_bridge once.
   - Home, Engine, Prelive, Backtest, Doo Prime, and Train Data all use st.session_state['last_df'].

2. New Train Data tab.
   - Loads maximum history using the selected API.
   - Auto-collects shared dataframe on refresh.
   - Shows row count increasing live.
   - Shows instant quant result.
   - Includes History Search by Day.
   - Can download training_dataset.csv.

3. Advanced Doo Prime analytics now appears in two places.
   - Original place under Home > Doo Prime.
   - New duplicate under Home > Launcher bottom.

4. MT5 vs Twelve confusion reduced.
   - Sidebar tells you MT5 is local-terminal based.
   - On Streamlit Cloud, use Twelve Data or Doo Bridge.
   - Direct MetaTrader5 package normally does not work on Streamlit Cloud because Cloud cannot open your Windows MT5 terminal.

How to run locally:
streamlit run adx_dashpoard.py

How to deploy Streamlit Cloud:
- Push this folder to GitHub.
- Main file: adx_dashpoard.py
- Use Twelve Data API key in the sidebar, or use Doo Bridge URL if you run a bridge service.
- Direct MT5 is for your Windows/local machine, not normal Streamlit Cloud hosting.
