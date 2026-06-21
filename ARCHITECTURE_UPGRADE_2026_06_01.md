# Flexible Multi-File Architecture Upgrade

This project is now organized so future upgrades can target one layer without damaging the original code.

## Run

```bash
streamlit run main.py
```

`main.py` calls `adx_dashpoard.py`, which calls `core.app_shell.run_app()`.

## Main architecture

| Layer | Main files | Purpose |
|---|---|---|
| App shell | `core/app_shell.py`, `core/app/runner.py`, `core/app/routes.py`, `core/app/registry.py`, `core/app/lifecycle.py`, `core/app/refresh.py` | Starts Streamlit, initializes state, applies style, auto-refreshes, then lazy-loads tabs safely. |
| Shared state | `core/common.py`, `core/system_contract.py`, `core/system_relations.py` | Keeps one source of truth for symbol, active tab, shared dataframe, account data, and system health. |
| Connectors | `core/data_connectors.py`, `core/connectors/data_connectors.py`, `core/connectors/websocket_feed.py` | MT5/TwelveData/WebSocket data access. Compatibility wrapper keeps old imports working. |
| Database | `core/database.py`, `core/storage/database.py` | SQLite/CSV persistence and export helpers. Compatibility wrapper keeps old imports working. |
| UI/UX | `core/styles.py`, `core/ui/styles.py`, `core/ui/helpers.py`, `core/ui/blocks.py`, `core/ui/effects.py`, `core/ui/relationship.py` | Global style, glass UI, popups, relationship panels, safe UI helper components. |
| Quant/ML | `core/quant_models.py`, `core/models/quant_models.py` | Indicators, feature engineering, bias/quality math, model helpers. |
| Tabs | `tabs/home.py`, `tabs/engine.py`, `tabs/train_data.py`, `tabs/pre_original.py`, `tabs/database_tab.py`, `tabs/profile.py` | Thin wrappers. Each tab points to its own split folder or module. |

## How to add a new future tab safely

1. Create a new file or folder under `tabs/`, for example `tabs/news/news_tab.py` with a `show()` function.
2. Add the tab name to `DEFAULT_TABS` in `core/common.py`.
3. Add one entry in `core/app/registry.py`:

```python
"News": TabSpec("News", "tabs.news.news_tab", icon="📰", notes="News/event risk panel."),
```

That is all. The lazy router will import it only when the tab is selected.

## Safe upgrade rules

- Do not edit `main.py` or `adx_dashpoard.py` unless the app entry point changes.
- Add new connector code under `core/connectors/`, then re-export compatibility functions in `core/data_connectors.py` only when old files need them.
- Add UI effects under `core/ui/`; keep `core/styles.py`, `core/uiux.py`, and `core/ui_helpers.py` as wrappers for backward compatibility.
- Add storage features under `core/storage/`; keep `core/database.py` as the stable import path.
- For a large tab upgrade, create a subfolder such as `tabs/home_split/` or `tabs/engine_split/`, then keep the top-level tab file as a small wrapper.

## What changed in this upgrade

- Added `core/app/registry.py` as the central tab map.
- Rebuilt `core/app/routes.py` to use lazy import from the registry.
- Fixed `tabs/pre_original.py` duplicate import line.
- Kept all old compatibility imports so existing upgraded code continues to work.
- Added this architecture guide for future copy/paste upgrades.
