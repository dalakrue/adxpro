2026-06-02 FINDER + HOME SYNC COPY FIX

What changed:
1) Finder selected-hour reversal is now synchronized with Home 10-point reversal logic.
   - Finder no longer decides reversal using only selected 4 rows.
   - It uses before context + selected hour + after context.
   - M1-like data uses 60 candles before vs 60 candles after for the reversal engine.
   - H1-like data uses 12 candles before vs 12 candles after.

2) Finder 10-point reversal table now uses Arrow-safe dataframe rendering.
   - Fixes PyArrow error:
     Could not convert '58.3%→46.7%' with type str: tried to convert to double

3) Home top copy button added.
   - At the top of Home: Build + Copy Home + Doo Analysis.
   - Includes Home data, Doo Prime Analysis metrics, Finder/reversal summaries, market analytics.
   - Excludes detailed per-position entry rows.

4) FutureWarning fixed in patched H1 resample helper.
   - Uses '1h' instead of deprecated 'H'.

Files added/changed:
- tabs/home_split/finder_home_sync_patch.py
- tabs/home_split/doo_prime_deep.py
- tabs/home_split/home.py

Run:
streamlit run main.py
