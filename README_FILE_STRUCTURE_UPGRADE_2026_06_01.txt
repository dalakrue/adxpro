FILE STRUCTURE UPGRADE - 2026-06-01

Goal:
- Keep the original app behavior working.
- Make the project easier to upgrade by separating app runner, UI, connectors, models, and storage.
- Keep compatibility wrappers, so older imports such as core.styles or core.data_connectors still work.

New upgrade-friendly structure:

core/app/
  runner.py       -> Streamlit app startup and page execution
  lifecycle.py    -> safe page wrapper, timing, relationship footer/header
  refresh.py      -> deferred auto-refresh logic
  routes.py       -> tab routing only

core/ui/
  styles.py       -> global CSS / glass UI / sidebar helpers
  blocks.py       -> reusable UI cards and headers
  helpers.py      -> shared UI helper functions
  relationship.py -> cross-tab UI relationship state

core/connectors/
  data_connectors.py -> MT5, TwelveData, Doo bridge data logic
  websocket_feed.py  -> websocket session feed logic

core/models/
  quant_models.py -> indicators / quant calculations / model helpers

core/storage/
  database.py     -> CSV / SQLite persistence helpers

tabs/doo_prime/
  account.py          -> future Doo Prime/MT5 account entry point
  home_analytics.py   -> future Doo Prime home analytics entry point

tabs/train/
  train_data.py       -> future train-data upgrade entry point

Compatibility preserved:
- core/app_shell.py still exposes run_app.
- core/styles.py still works.
- core/data_connectors.py still works.
- core/database.py still works.
- core/quant_models.py still works.
- core/websocket_feed.py still works.
- Existing tab imports still work.

Run:
  streamlit run main.py

Notes:
- __pycache__ folders were removed from this package.
- Original data files were kept.
- No trading logic was intentionally changed; this is a file-structure upgrade.
