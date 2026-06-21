Reliability Control Center Upgrade — 2026-06-14

Base: uploaded last working ZIP.

Added:
- New Home/Lunch open/close section: Reliability Control Center.
- Section appears after the Lunch metric/full metric area and before the extra copy/data visualization sections.
- Manual-run gated: stays idle until Run Calculating is clicked.
- Uses existing OHLC, history, regime, priority, forecast, and metric values only.
- No external APIs, no heavy models, no new prediction engines.

Dashboards inside Reliability Control Center:
1. Feature Leakage Guard
2. Data Quality + Market Feed Health
3. Regime State Reliability
4. Priority Anti-Constant Engine
5. MFE / MAE Exit Control
6. Market Maker Pressure Proxy
7. Distribution Shift / Wasserstein-style Drift
8. PCA-style / Factor Structure Dashboard
9. Anomaly and Shock Detector
10. Model Decay / Forecast Freshness

Copy integration:
- Reliability Control Center summary is appended to Copy Short.
- Full Reliability Control Center JSON is appended to Copy Full.
- Existing real copy button renderers remain untouched.

Validation:
- Python compileall completed successfully.
- ZIP integrity test completed successfully.
