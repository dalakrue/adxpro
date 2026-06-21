V17 HOME + SIDEBAR PLACEMENT UPGRADE

What changed:
1. Home tab order is now controlled from tabs/home.py:
   - All 10-Reversal / reverse-decision content appears first.
   - The <=3/10 calm table appears immediately under the reversal command center.
   - Copy + Refresh buttons appear together after reversal sections.
   - Original Home inner tab choice buttons appear after Copy + Refresh.
   - Remaining Launcher / Doo Prime / Doo Prime Analysis sections stay under the inner tab choice buttons.

2. Duplicate Home-top reversal banner was removed from the legacy Home body so the reversal block appears only once at the new top placement.

3. Sidebar now includes a top open/close field named "Top 10-Reversal status" before connector/settings controls.

Files changed:
- tabs/home.py
- tabs/home_split/legacy/implementation_parts/part_06.py
- core/navigation_parts/main.py

Original calculation logic was not changed. This is a placement/UI ordering upgrade.
