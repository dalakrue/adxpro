NEXT LEVEL UI/UX PATCH - 2026-06-09

What changed:
- Added core/ui/app_polish.py as a visual-only app shell polish layer.
- Added premium mobile-first CSS for buttons, cards, metrics, tables, tabs, sidebar, inputs, alerts, and charts.
- Added a real-app top header/status bar showing source, symbol, timeframe, active tab, row count, and phone/laptop mode.
- Kept all trading logic, calculations, functions, connectors, and tab render functions unchanged.
- Added the polish through core/app/runner.py so it applies globally and safely.

Run:
streamlit run adx_dashpoard.py

Safety:
This patch is additive. If a future Streamlit version ignores a CSS selector, the app still runs and the calculation engine is unaffected.
