Finder Reversal Detector Fix - 2026-06-02

What was fixed:
1. Finder no longer explains a reversal from only the selected candle.
2. Finder now builds PRE_WINDOW vs POST_WINDOW around the selected calendar time.
   - M1-like data: 60 candles before vs 60 candles after.
   - H1-like data: 12 candles before vs 12 candles after.
3. Added REVERSAL DETECTOR table:
   - before_move_% / after_move_% / delta_move_%
   - before_dve_% / after_dve_% / delta_dve_%
   - before_rising_eff_% / after_rising_eff_%
   - before_falling_eff_% / after_falling_eff_%
   - before_fat_tail_z / after_fat_tail_z
   - before_kurtosis / after_kurtosis
   - before_trust_% / after_trust_%
   - buy/sell rotation
   - reversal_strength 0-100
   - cause explanation
4. Finder export now includes:
   - FRAME INDEPENDENCE WARNING when all M1/H1 rows are identical.
   - SAME-AS-DOO METRICS with actual_interval.
   - REVERSAL DETECTOR BEFORE VS AFTER CSV.
5. Fixed context logic so Finder includes candles after the selected time, not only candles ending at the selected hour.
6. Added actual_interval detection so fake M1/H1 duplication is visible.

Important:
If you load only H1 candles, M1 600 and M1 60,000 cannot become real M1 analysis.
The app now warns instead of silently pretending those rows are independent.
For true M1 vs H1 difference, connect MT5/Doo Prime with real M1 history loaded.
