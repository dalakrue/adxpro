V25 SIDEBAR TIMER + METRIC/DOO + COPY FIX

Fixed:
1. Sidebar crash fixed:
   - Added _safe_log_event() inside core/navigation_parts/timer.py.
   - Timer Start/Reset no longer causes NameError.

2. Timer sound upgraded:
   - Final 1 minute now shows warning status.
   - Browser/phone beep attempts every 5 seconds from 1 minute left.
   - Time-up alarm still plays longer alarm and vibration when supported.

3. Sidebar UI mode section added:
   - Added Phone UI / Laptop UI buttons under Timer section.
   - Buttons align like tab-choice buttons.
   - Does not change calculation logic or connected data.

4. Home inner navigation changed:
   - Metric inner tab is first.
   - Doo Prime and Doo Prime Analysis are beside Metric.
   - Launcher inner tab is removed from visible Home flow.

5. Copy export fixed:
   - Metric inner-tab export is included in Home copy payload.
   - Raw positions, order rows, deal rows, and history rows are excluded.
   - Account summary keeps only safe top-level account/margin fields.

Validation:
- py_compile passed for all Python files under core/ and tabs/.

Run:
streamlit run main.py
