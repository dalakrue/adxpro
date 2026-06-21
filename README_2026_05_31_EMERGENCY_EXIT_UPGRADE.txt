Emergency Doo Prime Exit Decision Upgrade - 2026-05-31
======================================================

What was added
--------------
1) Added a new Emergency Exit metric beside Margin Level % in the Doo Prime real account stats row.
2) Added a new "Tomorrow Emergency Exit Decision Matrix" inside Advanced Live Doo Prime Analytics.
3) The matrix compares:
   - HOLD BOTH SIDES
   - EXIT ALL BUY NOW -> remaining SELL-only basket
   - EXIT ALL SELL NOW -> remaining BUY-only basket
4) It estimates:
   - margin level after each scenario
   - stop-out buffer
   - danger direction
   - loss per price point
   - points to stop-out
   - points to margin call
   - realized P/L if that basket is closed
   - whether current market pressure is dangerous or favorable for the remaining basket
5) Added paired BUY+SELL reduction candidates. These help reduce margin without making the account naked one-way.
6) Added emergency_exit_decision to the Home tab copy export so GPT can analyze the decision using your live data.

Important behavior
------------------
- The system does NOT execute trades.
- It is a risk-control dashboard only.
- It does not remove or replace the original code.
- It uses current account snapshot + open positions + Home/Do Prime market dataframe + quant_stack when available.

Why this was added
------------------
Your current problem is not simply BUY or SELL direction. The danger is that closing one full side can leave the remaining side naked and too close to the 30% broker stop-out level. This upgrade shows that risk numerically before you close a side.

Files changed
-------------
- tabs/account_split/implementation.py
- tabs/home_split/implementation.py

Run
---
streamlit run adx_dashpoard.py

or

streamlit run main.py
