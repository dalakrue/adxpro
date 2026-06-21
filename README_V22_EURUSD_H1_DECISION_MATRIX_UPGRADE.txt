V22 EURUSD H1 DECISION MATRIX UPGRADE

What was added without removing existing tabs/code:

1) New tab: EURUSD H1 Decision Matrix
- H1 is the main timeframe for bias, entry, exit, TP.
- M1 is used only for confirmation and pullback timing.
- M1 and H1 are never combined into one dataframe.

2) New required tables
- 10 Entry Decision Table
- 10 Direction Decision Table
- 10 Exit Decision Table
- 10 TP Decision Table
- Final Master EURUSD H1 Score summary

3) Extra EURUSD H1 filters
- Trend Capacity Used
- Pullback Readiness Score
- Pressure Acceleration
- Expected Remaining Move
- Position Survival Score
- Hold Quality Score

4) Session entry control
- Adds a session candidate table.
- Includes at least one Before-NY entry candidate rule.
- If full entry quality is not enough, it marks the candidate as Wait Pullback / Micro confirmation only instead of forcing a bad full entry.

5) 25-day hourly history
- The new tab shows a 25D H1 hour-by-hour history table.
- Home also includes the EURUSD H1 Matrix under the 10-Reversal Decision area.

6) Custom timeframe choice
- Added CUSTOM in timeframe selector.
- CUSTOM loads H1 and M1 separately.
- H1 is stored as main shared data.
- M1 is stored separately as confirmation data.
- In the Matrix panel, CUSTOM shows H1 history first and M1 confirmation history next.

7) Defaults changed
- Default symbol: EURUSD
- Default timeframe: H1
- Timeframe box choices: M1, M2, M5, M15, H1, H4, D1, CUSTOM
- API source order starts with Twelve Data first.

8) Copy data upgraded
- Sidebar Copy All Data JSON now includes eurusd_h1_decision_matrix and custom timeframe row counts.

Run:
streamlit run main.py
