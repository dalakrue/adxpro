V26 PHONE SIDEBAR + COPY + METRIC/HOME PATCH

Paste/replace these files into the project:
1) core/ui/legacy_impl/styles_impl.py
   - stronger mobile sidebar close: no leftover phone sidebar sliver
   - repeated close attempt after rerun
   - hides overlay and collapsed sidebar completely on <=768px

2) core/pro_terminal_uiux.py
   - render_mobile_copy_button is now self-contained inside Streamlit iframe
   - phone copy works using navigator.clipboard first, textarea fallback second

3) tabs/home.py
   - Home inner first tab is now Metric + Home
   - Metric and Home functions stay separate; only the visible tab is combined
   - 10-Reversal/Home decision panel appears above Metric in the combined tab
   - all home inner button clicks request phone sidebar close
   - new Copy Necessary Short Only phone-safe button added

4) tabs/eurusd_h1_matrix.py
   - Metric has Copy Necessary Short Only button
   - copy payload is short: symbol, timeframe, source, decision, direction, master/entry/hold/TP/exit, and 10 reverse-style factors
   - separate 25D factor tables remain independent and not mixed

Run:
streamlit run main.py
