2026-06-14 Clean Decision / System Trust / Regime UI patch

Goal:
- Reduce Home/Lunch and Regime tab visual overload without deleting any existing calculation, metric source, table source, chart source, export, copy function, ML table, or prediction logic.

Added / changed:
1. Decision Control Panel at the top of Lunch
   - Trade Status, Direction, Confidence %, Risk %, Best TP Zone, Danger SL Zone, Main Reason, Do-not-trade warning.

2. System Trust Center
   - Merges Reliability Control Center, Forecast Robustness, Data Quality, Leakage Guard, Drift, Anomaly, Forecast Freshness into one collapsed section.
   - Shows only summary metrics first.
   - All previous details remain inside Advanced Details.

3. Dynamic Entry Priority Center
   - Merges KNN Priority, Greedy Priority, Anti-Constant, Best Hour, and Best 2 Entries.
   - Shows Priority Rank 1-14, label, best 2 hours, movement score, constant score warning, and reason.
   - Priority detail table remains inside Advanced Details.

4. Regime Intelligence Center
   - Replaces the crowded Regime inner tab display.
   - Shows only Current Regime, Confidence, Reliability, Age, Shift Risk, Best Action, Trust Reason first.
   - Replaces every-hour regime display with a 25-Day Major Regime History Table that aggregates consecutive same-regime hours into periods.
   - Advanced metrics and similar historical regimes remain inside Advanced Details.

5. Copy Short / Copy Full
   - Appends the new Decision/System Trust/Dynamic Priority/Regime summary data.

Compatibility:
- Streamlit Cloud compatible.
- No external API.
- No heavy models.
- No new prediction engines.
- Uses existing OHLC/history/regime/priority/forecast/session-state metrics only.
