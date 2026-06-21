PRO TERMINAL UI/UX V2.1 FINAL PATCH
====================================

This patch is additive and keeps the original trading/reversal/data code intact.

Added / upgraded:
1. Smart Sidebar Pro polish
   - Sidebar expanders styled as trading-control panels.
   - Better active button glow, hover lift, compact mobile spacing.

2. Global command center on every main tab
   - Market Pulse
   - Reversal Danger
   - Margin Safety
   - Data Quality
   - Source

3. Popup alert layer
   - Reversal >= 7/10 warning
   - Margin danger warning
   - Fat-tail shock warning
   - Data quality warning

4. st.metric replacement styling
   - Glass card look
   - Hover lift animation
   - Smaller professional labels
   - Mobile-friendly size

5. Table UI upgrade
   - Better horizontal scroll
   - Sticky-header feel
   - Compact font
   - Rounded glass frame

6. Mobile alignment upgrade
   - 2-card mobile grid where possible
   - Bigger touch buttons
   - Smaller metric text
   - Better iPhone layout

7. Mobile copy helper
   - Adds clipboard fallback logic for browsers that block navigator.clipboard.
   - Existing copy buttons continue working; new helper can be reused in future tabs.

Changed files:
- core/pro_terminal_uiux.py
- core/app/runner.py

How to run:
1. unzip this project
2. cd new7
3. pip install -r requirements.txt
4. streamlit run main.py

Safety note:
This is visual/UI-only. It does not change order logic, connector logic, account logic, or the 10-Reversal math engine.
