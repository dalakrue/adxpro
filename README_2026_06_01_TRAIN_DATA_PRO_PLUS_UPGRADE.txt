Train Data Pro+ Upgrade - 2026-06-01

Copy-paste/run form:
1. Unzip this folder.
2. Open terminal in the unzipped new7 folder.
3. Run: streamlit run main.py --server.port 8501

What changed:
- Upgraded tabs/train_data.py only; no original connector, Home, Engine, Pre Original, or Profile logic was removed.
- Train Data still uses the global sidebar dataframe st.session_state['last_df']; it does not open a second MT5/TwelveData connection.
- Added Cross Tab Link section to verify shared data relation between Home, Engine, Train Data, Pre Original, database, and session state.
- Added Training Readiness score with practical reasons when the dataset is too small, one-sided, or weak.
- Added Exit Label Builder for BUY-side and SELL-side basket pressure research.
- Added safer exit labels: EXIT_BUY_RISK, HOLD_BUY_OK, EXIT_SELL_RISK, HOLD_SELL_OK, WAIT.
- Added save support for exit-label memory back into training_data_cache.
- Kept existing Live Training, Model Validation, Math/ML Diagnostics, History Search, Feature Health, Session Edge, and Database Center.
- Full project passes python compileall syntax check.

Important trading note:
This Train Data upgrade creates analytics labels and validation tables only. It does not place, close, or modify broker orders.
