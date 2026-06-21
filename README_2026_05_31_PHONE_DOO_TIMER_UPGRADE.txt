PHONE + DOO PRIME + TIMER UPGRADE - 2026-05-31

What was upgraded:
1) Timer sound is longer
   - Sidebar timer now plays an approximately 8-second alarm.
   - Pre Original trade countdown timer also plays an approximately 8-second alarm.
   - Phone vibration pattern is longer when the browser supports vibration.

2) Doo Prime Analysis inner tab is stronger and more efficient
   - Changed from 4 separate heavy connector calls to 1 efficient M1 base fetch.
   - M1 600 and M1 60,000 blocks are built from the M1 base.
   - H1 600 and H1 60,000 blocks are locally resampled from the M1 base, so the panel is faster and less likely to blank.
   - Each block now shows a reliability/quality label: FULL, PARTIAL BUT USABLE, USABLE FALLBACK, DEMO / NOT LIVE, or NO DATA.
   - Combined tab now includes quality, average trust, and a practical reading rule.
   - 10-minute auto-fetch is enabled by default and can be toggled off in the panel.

3) Auto refresh changed to 10 minutes
   - Global Streamlit app refresh is now 600,000 ms / 10 minutes.
   - maybe_refresh default is now 600 seconds.
   - Doo Prime deep analysis page refresh is now 10 minutes.

4) Phone alignment upgraded
   - Phone mode now uses near-full screen width.
   - Streamlit st.columns no longer collapse into one metric per row on small phone screens.
   - Metric/button rows use compact responsive grid columns.
   - Padding and margins are reduced so phone mode is wider and more dashboard-like.

Changed files:
- core/app_shell.py
- core/common.py
- core/navigation.py
- core/styles.py
- tabs/home_split/doo_prime_deep.py
- tabs/pre_clean_split/timer.py

How to run:
1. Extract this ZIP.
2. Open PowerShell inside quant_app_upgrade.
3. Run:
   streamlit run adx_dashpoard.py

Important:
- If a Doo Prime block says DEMO / NOT LIVE, do not rely on that block for real-money exit timing.
- For real decisions, prioritize blocks that say FULL or PARTIAL BUT USABLE.
- H1 60,000 may show partial because it is derived locally from M1 history to avoid repeated slow connector calls.
