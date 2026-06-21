2026-06-11 Advanced Efficiency / Reliability Control Center

Additive upgrade using existing calculations only. No new ML models, no option pricing,
no Black-Scholes, no option chain data. Existing charts, tables, copy buttons, JSON
outputs, tabs, and logic are preserved.

Added:
- Important Fact Control Center in Lunch, Data Visualization, and Finder wrappers.
- Regime Gate Status and Regime Permission.
- Greedy Priority display layer and Decision Vote Board.
- Multi-window Profit Factor Consensus PF50/PF100/PF200/PF500.
- Market Health, Execution Quality, Survival, Cost/Friction, Tail Risk dashboards.
- Drawdown Cluster, Market Stability State, Drift Warning.
- Forecast Greeks: Delta, Gamma, Theta, Vega display-only synthetic scores.
- Forecast Aging: Age, Freshness, Decay %.
- Volatility Surface H1/H4/D1/W1, compression detector, expected move.
- Edge Location Map and Grid Placement Helper inside lazy expanders.
- Copy Full output includes all new metrics without removing old copy content.

Performance:
- Uses existing session results and cached/stored data.
- Heavy calculations remain behind existing Run Calculation buttons.
- Expanders are lazy UI sections and compact by default for iPhone 11 Pro.
