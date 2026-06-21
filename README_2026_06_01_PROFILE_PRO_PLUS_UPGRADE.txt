PROFILE TAB PRO PLUS UPGRADE - 2026-06-01

What changed:
1. Profile tab remains backward compatible through tabs/profile.py.
2. Added Profile Score / Readiness Gate section.
   - Scores live data, connector status, margin level, position count, missing data, and duplicate rows.
   - Saves snapshots to data/profile_score_history.csv.
3. Added Daily Trading Plan section.
   - Saves session plan, prepared bias, max loss limit, exit rule, and invalidation rule.
   - Saves to data/profile_daily_plans.csv.
4. Added Performance Summary section.
   - Reads profile_score_history, profile_daily_plans, profile_risk_checklist, risk_snapshots, engine_mix_snapshots, and saved_notes.
   - Adds search, open/close table view, and numeric summary.
5. Strengthened profile helpers.
   - New safe profile_snapshot_dict().
   - New profile_readiness_score().
   - New summarize_numeric_table().
6. Kept original Profile modules and made .bak_profile_original backups.
7. No connector logic changed. No Home / Engine / Train Data / Pre Original routing changed.

Run:
streamlit run main.py

Important:
This Profile score is only a readiness/risk-control display. It does not open, close, or recommend live trade execution.
