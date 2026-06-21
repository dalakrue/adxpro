V6 FINAL UI + LOGIC PATCH

What changed:
1. Fixed sidebar PRO CONTROL alignment so the label no longer crops on phone/sidebar width.
2. Tightened Home top hero spacing to match the uploaded screenshot: smaller title, compact cards, cleaner mobile grid.
3. Added a global compact status strip on every tab: Tab, Source, Market, Rows, Reversal.
4. Improved shared dataframe detection across old/new state keys, so the UI avoids Rows 0 when valid data is already loaded.
5. Hid heavy floating assistant/pulse ring from the top view to make tab switching and mobile scrolling faster.
6. Kept the V5 strict reversal filter intact: trend-before-reversal + move quality + 3-candle confirmation + 4-hour reversal-zone counting.

Files added/changed:
- core/v6_final_ui_logic_patch.py
- core/app/runner.py
- tabs/home_split/pro_terminal_uiux.py

Original connector, order, account, MT5, TwelveData, and tab functions were not removed.
