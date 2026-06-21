HOME REVERSAL 9/10 DETECTOR FIX - 2026-06-02

What changed:
1. Fixed the 10-point reversal engine so it no longer averages M1 and H1 detector rows.
   - Old behavior: averaged all Before/After rows, causing strong M1 reversal evidence to dilute to 6/10.
   - New behavior: evaluates every Before/After detector row independently and uses the strongest valid frame.

2. Fixed the 2026-05-28 14:00 case to show 9/10 from the real open Reversal Detector evidence.
   - Direction Rotation: YES
   - Kurtosis Explosion: YES
   - Sell to Buy Flip: YES
   - Rising Efficiency: YES
   - Fat Tail Z: YES
   - Buy Ratio Increase: YES
   - Sell Ratio Decrease: YES
   - Trust Confirmation: YES
   - Reversal Strength: YES
   - DVE Rotation: WATCH only, shown in the table but not counted as a hard confirmation point.

3. Added Home st.metric block immediately after API connection / shared dataframe load:
   - Current Reversal Score
   - Last Time >= 7/10
   - Detector Source

4. Added automatic scan of loaded current candle data to find the last completed hour that reached >= 7/10.
   - No Finder tab is required.
   - It updates from the same shared dataframe used by Home and Doo Prime Analysis.

Files changed:
- tabs/home_split/doo_prime_deep.py

Run:
streamlit run main.py
