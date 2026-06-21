2026-06-11 ADDITIVE HISTORY + POWER BI VISUAL CONTROL CENTER

Base: uploaded last working ZIP.

Rules followed:
- No existing table/chart/ML table/history chart/copy button/tab/function/logic was deleted or renamed.
- No new ML models or new prediction engines were added.
- New sections use only stored DataFrame/session calculation outputs and filtering.
- Heavy calculations remain behind existing Run Calculating buttons.
- Added controls are phone-safe and use filtering/replay/summary views instead of retraining.

Added Lunch tab UI:
- History Control Center above/additional to the existing history area.
- Choice buttons: Today, Last 2 Days, Last 5 Days, Last 10 Days, Last 25 Days, Custom Day, Custom Hour, NY/London Overlap Only, High Quality Only, High Risk Only, Conflict Only, Counter Trend Only, Best Hours, Worst Hours.
- Regime History Table columns: Time, H1/H4/D1 regime, regime direction, prediction direction, Master, Entry, Hold, Exit Risk, TP, Market Quality, Forecast Agreement, Reliability, Conflict, Counter Trend, Final Decision.
- Selectors: Day, Hour, Regime, Decision, Reliability Range, Market Quality Range.

Added Data Visualization tab UI:
- Power BI Visualization Control Center.
- Buttons/toggles: Next 3H/6H/12H, Replay Last 1/2/5 Days, Today Only, NY/London Only, Show Previous/Future Prediction, Show Risk Band, Show Regime/Reliability/Conflict Overlay.
- Original Power BI chart remains unchanged; controls are stored for overlay/replay interpretation without modifying existing output values.
- Regime Prediction Panel with st.metric values and table.
- Self Backtest Center using existing stored summary/history.

Performance:
- iPhone 11 Pro safe: no auto heavy calculation, limited table rows, no model training.
- Uses cached/session outputs and filtered DataFrame slices only.
