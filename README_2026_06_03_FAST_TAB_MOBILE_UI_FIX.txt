FAST TAB + MOBILE UI FIX — 2026-06-03

Priority fixes applied without changing trading calculations, reversal logic, connector functions, or old tab functions:

1) Faster tab switching
- Navigation now marks tab clicks as UI-only reruns.
- App runner skips auto connector refresh, maintenance, and repair cycle during tab opening.
- Existing refresh still runs normally outside active navigation.

2) Faster Home opening
- Home pro terminal visual snapshot no longer copies large market dataframes.
- It reads existing shared dataframe directly for row/close summaries only.

3) Faster inner-tab opening
- Same fast-navigation guard prevents deep refresh/maintenance from blocking inner/tab transitions.
- Doo/Finder original functions remain intact.

4) Mobile UI alignment
- Replaced global visual layer with the light blue/white glassmorphism terminal style shown in the screenshot.
- Mobile columns wrap into 2-card grids.
- Buttons are bigger touch targets, with less overflow.
- Sidebar width is capped for phone screens.
- Tables keep horizontal scroll instead of breaking layout.

5) Copy on mobile
- Global CSS/JS keeps buttons touch-friendly.
- Existing copy components remain; fallback text boxes remain if browser clipboard blocks copy.

Run:
python -m streamlit run main.py

If Streamlit is not installed:
pip install -r requirements.txt
