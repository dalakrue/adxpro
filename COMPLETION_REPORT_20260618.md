# ADX Quant Pro / new7 — EURUSD H1 Canonical Synchronization Completion Report

## Delivery scope

The uploaded project was inspected and modified in place. The complete project is delivered, not a patch. The protected Full Metric implementation in `tabs/eurusd_h1_matrix.py` was not modified; its verified SHA-256 remains:

`fe0797ab30f469f3ea748bc66a690b18a68aaf91306ac33c797bdcdcf6e60682`

## Main files modified or added

- `ui/table_ordering_20260618.py`
- `tabs/antd_page_router_20260615.py`
- `core/full_metric_canonical_adapter_20260618.py`
- `core/canonical_runtime_20260617.py`
- `ui/full_metric_shared_renderer_20260618.py` (new)
- `tabs/final_three_center_upgrade_20260614.py`
- `core/ai_canonical_grounding_20260618.py` (new)
- `tabs/dinner_morning_data_patch_20260614.py`
- `tabs/dinner_unified_center_20260617.py`
- `tabs/final_lunch_upgrade_20260617.py`
- `core/news_event_store_20260618.py` (new)
- `core/nlp_related_priority_20260615.py`
- `ui/nlp_research_panel.py`
- `tabs/research.py`
- `tabs/home.py`
- `ui/liquid_menu_popup_20260615.py`
- `core/finnhub_connector.py`
- `core/decision_product_engine_20260617.py`
- `tests/test_end_to_end_sync_regressions_20260618.py` (new)

## Main logical fixes

### Protected Full Metric source of truth

- Preserved the protected Full Metric formulas, thresholds, ten reverse-decision factors, direction logic, scores, histories, exports, and source file byte-for-byte.
- Added one shared read-only renderer for the complete cached Full Metric result.
- Lunch and Dinner now consume the same protected result instead of maintaining incomplete competing renderers.
- Supporting layers may lower confidence or protect with WAIT, but cannot reverse a canonical BUY to SELL or SELL to BUY.

### Current completed H1 first

- Added one chronological history helper that normalizes timestamps, removes invalid/future rows, sorts latest completed H1 first, and uses `.head(display_rows)` after sorting.
- Removed the active Finder defect that sorted newest-first and then used `.tail(display_rows)`.
- Added a focused regression test that fails when old rows are returned after a newest-first sort.
- Kept chronological history ordering separate from priority/opportunity ordering.

### Canonical synchronization

- Added shared identity validation for run ID, generation, symbol, timeframe, latest completed H1 candle, and data signature.
- Canonical results now expose the required Full Metric, history, regime, alpha/delta, reliability, Power BI, Finder, NLP, Research, conflict, data-quality, actionable-decision, opportunity, and freshness fields.
- Supporting components that are stale or mismatched are excluded from trade approval and produce a safe WAIT action.
- Complete generations remain atomically published only after successful calculation.

### Dinner restoration

- Restored the active Dinner inner tabs as `Regime Summary`, `Combined Logic`, and `AI Assistant`.
- Regime Summary uses the canonical completed-H1 timestamp and current-first history.
- Combined Logic merges Full Metric, regime, alpha/delta, Power BI, KNN/Greedy, Research/NLP, reliability, conflict, protection, and opportunities without generating a separate direction.
- AI Assistant is grounded in the canonical result and returns the required decision-first response order.

### NLP API placement and ten-day persistence

- Settings remains the only active full Finnhub API-key input location.
- Sidebar uses compact connection status without a key input.
- Research NLP uses the configured key and does not display a duplicate input.
- Added a secret-safe SQLite news-event ledger in the existing project database.
- Genuine Finnhub/cache/RSS/local/session articles are merged, normalized, future-filtered, deduplicated, persisted, ranked, and shown over a ten-day window.
- At least ten rows are shown when ten genuine rows exist; fewer rows are reported honestly without placeholders.
- API keys and authorization values are stripped before persistence.

### Two daily opportunity evaluations

- Canonical opportunity selection always evaluates two slots without forcing a trade.
- Statuses are `QUALIFIED ENTRY`, `WATCH CANDIDATE`, or `NO ENTRY / WAIT`.
- The second opportunity must be materially distinct or at least two H1 candles apart; otherwise a safe explicit WAIT slot is shown.
- Negative expected value, stale data, critical conflicts, poor quality/reliability, unacceptable exit risk, or strong M1 timing opposition block qualification.

### Research reuse and performance

- Existing Research/NLP confirmations are reused inside Lunch, Dinner, Finder, and AI grounding.
- Removed duplicate inner-tab Run Calculation controls; Settings remains the calculation gate.
- Changed tab-switch behavior to reuse the current canonical generation instead of forcing recalculation.
- Heavy results, history, Power BI, Research/NLP, ranking, and opportunity tables are reused from canonical caches.
- Active renderers are route consolidated; legacy compatibility code remains but cannot override the authoritative active paths.

## Tests actually executed

- `python -m pytest -q` — **64 passed in 9.85s**
- `python -m compileall -q .` — passed
- Active import validation — **15 active modules imported successfully**
- `python tools/validate_architecture.py` — passed
- `python tools/validate_final_sync_20260617.py` — passed
- `python tools/validate_finnhub_nlp_restore_20260617.py` — passed
- Streamlit server startup and `/_stcore/health` check — returned **ok**
- Streamlit `AppTest.from_file('app.py')` — **0 exceptions**
- Protected Full Metric SHA-256 verification — passed

The automated suite covers current-first ordering, chronological-versus-priority views, completed-H1 selection, future-data rejection, canonical identity, Lunch/Dinner synchronization, Dinner AI routing and grounding, NLP input placement, ten-day persistence and deduplication, two opportunities without forced entry, stale-generation WAIT protection, cache/export preservation, causality, hidden-tab laziness, and mobile low-heat rules.

A live Finnhub request was not executed because no user API secret was used during testing. The existing connector and NLP integration validator passed, and tests confirm secrets are not persisted.

## Main Streamlit entry file

`app.py`

## Installation and run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Addendum — existing Regime inner section restored inside Full Metric History

The active Full Metric renderer and the restored original Lunch history renderer now both call `ui/full_metric_regime_inner_renderer_20260618.py`.

This display-only bridge keeps the existing Regime summary, KNN/Greedy Regime Priority table, Regime History Data table, persisted Major Regime History, and regime-related Full Metric columns directly visible whenever Full Metric Detail + History is opened. It contains no second Run button, nested expander, or hidden tab, and it does not invoke a separate regime calculation.

Current validation after this addendum:

- `python -m compileall -q .` — passed
- `pytest -q` — **67 passed**
- architecture validator — passed
- final synchronization validator — passed
- Finnhub/NLP/Lunch/Research validator — passed
- protected Full Metric SHA-256 — unchanged
