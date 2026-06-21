# 2026-06-19 Timezone + Lunch Restore Fix

Fixed the crash:

`TypeError: Invalid comparison between dtype=datetime64[us, UTC] and Timestamp`

Changed `tabs/home_split/v19_one_field_reversal_metric_patch.py` so the Doo Finder selected-day and selected-hour filters create timestamps with the same timezone mode as `data["time"]`. This prevents UTC-aware candle data from being compared with naive `pd.Timestamp(chosen_date)`.

Restored Lunch visibility:

- Kept Full Metric Details + History visible as a closed open/close field.
- Kept Synced PowerBI Price Projection + Actual vs Error visible as a closed open/close field.
- Kept Master Decision + Reliability + Priority Center.
- Added `Open / Close — Restored All Original Lunch Fields`, closed by default, so older hidden Lunch/Home sections remain available without long mobile scrolling.

No calculation logic, ML logic, Full Metric logic, or PowerBI prediction logic was removed.
