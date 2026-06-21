# Database Migration — 2026-06-19

Migration is automatic, additive, and runs when the trust history store is first opened. Existing tables and rows are not dropped.

New tables in `data/quant_app.sqlite3`:

- `settled_forecast_ledger_v3`
- `forecast_method_ledger_v3`
- `trust_validation_snapshots_v3`

New indexes cover forecast origin, target, horizon, H1/H4/D1 regime, session, calculation ID, and record status/target.

Settlement policy:

1. Insert the original forecast once with `PENDING` status.
2. Wait until the target H1 candle is fully available.
3. Update outcome-only fields and set `SETTLED`.
4. Never overwrite predicted price, probabilities, intervals, direction, reason, or calculation identity.
5. Mark malformed rows `INVALID`; reserve `EXCLUDED` for data-quality/leakage exclusions.

The migration also attempts a one-time read-only backfill from the existing prediction ledger when genuine legacy tables are present and the new ledger is empty. A backup is recommended before the first production deployment, although the migration itself does not delete existing history.
