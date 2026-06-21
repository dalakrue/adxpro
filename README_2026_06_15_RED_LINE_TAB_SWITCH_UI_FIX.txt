2026-06-15 Red Prediction + Tab Switch + UI polish fix

- Fixed Lunch Red Prediction Line so it can render from current Lunch OHLC data when synced PowerBI cache is not populated yet.
- Original synced PowerBI projection remains unchanged and still overrides the fallback after it is run.
- Added streamlit-option-menu as a lightweight, safe tab-choice library. All imports are defensive; app falls back to Streamlit radio/selectbox without crashing.
- Added mobile-friendly soft background / pop-up / motion CSS with prefers-reduced-motion support.
- No external APIs, no heavy models, no formula changes, no deletion of existing logic.
