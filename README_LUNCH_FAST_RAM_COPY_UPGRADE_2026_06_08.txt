LUNCH FAST / RAM / DATA / COPY BUTTON UPGRADE — 2026-06-08

Changed files:
- tabs/home.py
- core/pro_terminal_uiux.py

What was upgraded:
1. Lunch opens faster
   - Heavy 25-day reversal scan no longer runs automatically just because the Lunch tab opens.
   - Scan is triggered only by Run Calculating / Refresh or an explicit force flag.

2. Lower RAM and less rerun work
   - Lunch metric calculation is cached with a lightweight data signature.
   - Metric tables rebuild only when data changes or the user presses Run Calculating again.
   - Copy All text is cached and reused until source data/calculation/export state changes.

3. More reliable/correct copy data
   - Latest shared market data in Copy All is now a clean sorted OHLC tail.
   - Duplicate timestamps are removed and numeric OHLC values are coerced before export.
   - Export size is limited to compact recent rows to avoid freezing phones and Streamlit reruns.

4. More beautiful copy button UI/UX
   - Copy buttons now use a brighter gradient, rounded glass style, hover shine, press animation, and stronger mobile tap behavior.
   - Existing clipboard fallback remains in place for phone browsers that block clipboard access.

Validation:
- python -m py_compile passed for tabs/home.py, core/pro_terminal_uiux.py, core/navigation_parts/main.py, and core/app/runner.py.
