# Streamlit Cloud import and mobile E2E fix — 2026-06-19

## Fixed

- Removed the runtime dependency on `core.ui.legacy_impl.styles_impl_parts` by making `styles_impl.py` self-contained.
- Kept the archived split parts, but the deployed app no longer needs them to import styles.
- Added project-root bootstrap logic to `app.py` for reliable absolute imports on Streamlit Cloud.
- Replaced nested deployment requirements with one complete root `requirements.txt`.
- Kept `MetaTrader5` out of Linux/Streamlit Cloud requirements; Windows users use `requirements-windows-mt5.txt`.
- Preserved the Settings mobile API paste boxes, Twelve Data/MT5 connector, Finnhub, timer, logout and one-click Lunch workflow.

## Validation

- Streamlit server health endpoint returned `ok` and HTTP 200.
- `core.ui.styles`, `core.styles`, Settings router and `app` imported successfully.
- Styles imported successfully even with `styles_impl_parts` temporarily removed.
- Mobile AppTest flow passed: Guest → Phone mode → paste/save key → Run/Open Lunch → Dinner → Lunch → Settings.
- Focused regression suite: 40 tests passed.
