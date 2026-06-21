V20 10-Reversal Regime Shift Restore

Changed:
1. Replaced the old 3-Point Change Pack metric with Regime Shift Indicator.
   - Green: CALM / RESET
   - Blue: NEUTRAL
   - Orange: WATCH SHIFT
   - Red: DANGER SHIFT
   - Uses now / previous / previous-previous locked 10-Reversal score, speed, acceleration, and mean deviation.

2. Changed Last Hour <=3/10 metric behavior.
   - It no longer shows only YES/NO.
   - It now shows the latest hour found in the 25D scan where score <= 3/10, with the score as delta.

3. Restored 25D locked >=8/10 history table.
   - Shows closed-hour 10-Reversal history rows where score >= 8/10.
   - Includes out-of-10 score field.

4. Moved <=3/10 table directly below the >=8/10 history section.
   - Shows calm/reset rows from the same 25D scan.

Files changed:
- tabs/home.py
- tabs/home_split/v19_one_field_reversal_metric_patch.py

Original calculation logic is not changed. This is UI and table placement only.
