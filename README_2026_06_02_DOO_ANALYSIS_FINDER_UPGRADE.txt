Doo Prime Analysis Finder Upgrade - 2026-06-02

What changed:
1. Removed visible inner choices from Doo Prime Analysis:
   - M1 600
   - M1 60,000
   - H1 600
   - H1 60,000
   - Combined

2. Kept the old calculation functions internally so Data Modeling, Home Copy, and Finder can still reuse the computed data without breaking the original code.

3. Added a new Doo Prime Analysis inner tool:
   - Finder

Finder function:
- Search by Year, Month, Day, and Hour.
- Shows only the selected one-hour candle/modeling data.
- Adds reaction fields: body, range, return %, direction, upper wick, lower wick, reaction note.
- Shows metrics for rows, hour move %, BUY candles, SELL candles, and last close.
- Adds a mobile-safe copy button: "Copy This Finder Hour Data".
- Adds fallback copy text if browser/mobile blocks clipboard.

File changed:
- tabs/home_split/doo_prime_deep.py

Run:
streamlit run main.py
