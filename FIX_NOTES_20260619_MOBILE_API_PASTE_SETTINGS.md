# 2026-06-19 Mobile API Paste + Settings Fix

## Fixed
- Added a paste-friendly **Mobile API Key Paste Center** inside the existing Settings page.
- Added large mobile-safe textarea inputs for:
  - Twelve Data API key
  - Finnhub API key
  - NLP / AI Assistant API key
- Added Save / Clear / Connect / Test buttons with full-width mobile-friendly layout.
- Added mobile CSS so iPhone/Safari can focus and paste into API fields more reliably.
- Kept all existing calculation, prediction, regime, Lunch, PowerBI, and trading logic unchanged.

## Validation
- `python -m py_compile tabs/antd_page_router_20260615.py` passed.
- `python -m compileall -q tabs core app.py main.py adx_dashpoard.py` passed.
