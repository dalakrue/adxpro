2026-06-01 Doo Prime Account + UIUX Fix

Changes made additively without removing the upgraded basket-profit gate and modeling features:

1) Restored original Doo Prime account workflow inside Doo Prime > Account.
   - Added visible "Read Real Doo Prime MT5 Account" button inside Account.
   - This reads local MT5/Doo Prime account data directly and does not require the sidebar market connector.
   - Keep Doo Prime MT5 open and logged in before pressing it.

2) Added direct market connector buttons inside Doo Prime Account.
   - MT5 M1 Market Connect
   - Twelve M1 Market Connect
   These are optional direct controls for users who do not want to rely only on the sidebar connector.

3) Kept upgraded safety logic.
   - Exit BUY/SELL still considers basket P/L and profitable-side percentage.
   - Full confirmation remains stricter than WATCH.

4) Improved open/close field UIUX.
   - Smaller transparent glass panels.
   - Softer border.
   - Animated glass pop effect.
   - Compact button and metric styling.

Run:
  streamlit run adx_dashpoard.py --server.address 0.0.0.0 --server.port 8501
