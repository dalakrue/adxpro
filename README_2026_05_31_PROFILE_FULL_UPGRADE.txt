PROFILE FULL UPGRADE - 2026-05-31

What changed:
- Upgraded Profile tab only inside tabs/profile_dashboard_split.
- Kept original wrapper tabs/profile.py import path unchanged.
- Added Overview, Edit Profile, Risk Checklist, Data Health, Notes, History, Settings, Train Memory, Guide, Activity, and System Health tabs.
- Added safer state repair, safe CSV loading/saving, mobile-friendly CSS, export buttons, and per-tab crash isolation.
- No global tab routing was changed. Existing Home, Engine, Train Data, Pre Original, and Profile routing stays the same.

Run:
streamlit run adx_dashpoard.py
or
streamlit run main.py
