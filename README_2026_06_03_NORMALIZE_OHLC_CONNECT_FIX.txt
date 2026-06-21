2026-06-03 FIX: Connect failed: name '_normalize_ohlc' is not defined

WHAT WAS WRONG
- core/connectors/data_parts/session.py used _normalize_ohlc(), resample_ohlc(), and _clean_symbol()
  but did not import them from core.connectors.data_parts.utils.
- The helper existed in utils.py and was re-exported by core.data_connectors, but the split session module
  still had missing local imports. That caused connection failure during MT5/TwelveData/Doo Bridge connect.

WHAT WAS FIXED
- Added explicit imports in core/connectors/data_parts/session.py:
  _clean_symbol
  _normalize_ohlc
  resample_ohlc
  TWELVE_INTERVALS
- Confirmed core.data_connectors exports _normalize_ohlc correctly.
- Ran Python compile check successfully.
- Ran import checks for main, app runner, app shell, data connectors, and home command center successfully.

RUN
1. Extract ZIP
2. Open terminal inside new7 folder
3. pip install -r requirements.txt
4. streamlit run main.py

IMPORTANT
- This patch is non-destructive. It does not change your original trading logic.
- It only fixes the missing connector imports that blocked the app from connecting.
