2026-06-03 PRO TRADING TERMINAL UI/UX UPGRADE
================================================

Goal
----
Make the Streamlit app look like a professional trading terminal without changing the original trading logic, connector logic, 10-Reversal engine, Doo Prime account logic, or Finder calculations.

Files Added
-----------
1) core/pro_terminal_uiux.py
   - Global professional terminal CSS layer.
   - Dynamic market background modes:
     * Calm = blue gradient + moving grid/particles
     * Trend = green pulse mode when ADX-like state is strong
     * Danger = orange/red warning mode when reversal score is 7/10+
   - Glassmorphism cards, animated metric hover, sidebar animation, pulse styling.

2) tabs/home_split/pro_terminal_uiux.py
   - Home professional dashboard widgets.
   - 3D hero cards: Account Health, Market Pulse, Reversal Danger, Margin Safety.
   - Live Market Pulse Ring.
   - TradingView-style Market Health heatmap.
   - 10-Reversal Timeline expander for last 25-day scan state.
   - Floating Quant Assistant.
   - Finder wrapper: all Finder/Doo metric controls are inside one open/close glass field.

Files Updated
-------------
1) core/app/runner.py
   - Applies pro terminal CSS after the existing styles.
   - Non-destructive: only visual CSS injection.

2) tabs/home.py
   - Renders the new professional terminal dashboard before the original Home content.
   - Original Home implementation still runs unchanged.

3) tabs/home_split/doo_prime_deep.py
   - Installs the Finder open/close UI wrapper after the existing Finder and 10-Reversal patches.
   - Original Finder calculations remain unchanged.

What Was Upgraded
-----------------
✅ Glassmorphism Pro UI
✅ Dynamic Market Background
✅ Animated Metric Cards
✅ Reversal Alert Popup when score >= 7/10
✅ TradingView-style Market Health Heatmap
✅ Floating Quant Assistant
✅ Animated Sidebar
✅ Live Market Pulse Ring
✅ 3D Hero Dashboard
✅ Reversal Timeline open/close section
✅ Finder top cleanup: Finder is grouped into one open/close field

Safety Notes
------------
- No broker order logic changed.
- No reversal calculation logic changed.
- No MT5/TwelveData connector logic changed.
- No database schema changed.
- This is a UI/UX wrapper layer that reads existing session_state and Doo/Finder results.

Run
---
streamlit run main.py

If main.py fails in your environment, use:
streamlit run adx_dashpoard.py
