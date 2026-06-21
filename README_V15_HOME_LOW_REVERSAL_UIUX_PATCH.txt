V15 HOME LOW-REVERSAL TABLE + UIUX PATCH

What changed:
1. Home tab now adds one open/close field:
   ✅ Open / Close — 10-Reversal Calm Table ≤ 3/10

2. The new table shows all locked 25D scan rows where 10-Reversal Decision is 3/10 or lower.
   It includes:
   - Today calm rows
   - Full 25D calm rows
   - Metrics for total rows, today rows, lowest score, latest calm hour

3. No trading logic was changed.
   The patch only reads the existing Home/Finder locked 25D reversal scan.

4. UI/UX upgraded:
   - Home open/close fields get glass popup cards
   - Moving background effect stays active
   - Animated pop-up effect applied to command-center cards and expanders
   - Mobile-friendly card spacing preserved

Main files changed:
- tabs/home.py
- core/pro_terminal_uiux.py
