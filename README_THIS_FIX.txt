FIXED VERSION - 2026-05-31

What was fixed:
1. CSS NameError: name 'background' is not defined
   - Fixed unescaped CSS braces in core/styles.py.
   - Added cleaner global ocean/glass CSS and expander styling.

2. Home GPT copy export
   - Copy export is now inside a closed expander so Home is not huge/confusing.
   - The copy payload now includes Advanced Doo Prime 4-frame metrics:
     M1 600, M1 60000, H1 600, H1 60000.
   - It builds these from the already-connected/shared Doo Prime dataframe even if you did not open the inner tab first.

3. Weekend / closed-market price and fat-tail logic
   - Price window change now falls back to nearest previous/second-last close instead of fake zero/N/A.
   - Fat Tail Z uses the latest real non-zero close-to-close return when the newest visible candle is flat/duplicated.
   - Copy output includes last_close, previous_close, last_close_delta_pct, effective_return_pct, and fat-tail source note.

4. Margin change display
   - Per-second/per-minute/per-hour margin change no longer stays at N/A forever.
   - Once two real account snapshots exist, it uses the best available snapshot.
   - If full 1h history is not built yet, it clearly says it uses the last-two-snapshot fallback.

5. Sidebar timer
   - Added Trade Timer / Sound Alert in the sidebar.
   - When timer reaches 0, browser attempts beep sound and phone vibration.

How to run:
1. Extract this ZIP.
2. Open PowerShell inside quant_app_upgrade.
3. Run:
   streamlit run adx_dashpoard.py

Changed main files:
- core/styles.py
- core/navigation.py
- tabs/home_split/implementation.py
