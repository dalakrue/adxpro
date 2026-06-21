# Architecture and Call Graph — Canonical, Lazy and History-First

## Startup and rendering

```text
app.py
  -> adx_dashpoard.main()
    -> core.app_shell.run_app()
      -> core.app.runner.run_app()
        -> authentication / state initialization
        -> begin_rerun(session_state)
        -> guarded authenticated new-H1 startup (existing)
        -> navigation resolution
        -> ensure_shared_calculation_result(force=False) [read-only adapter]
        -> build_runtime_context(...)
        -> core.app.routes.load_tab(active_page)
          -> tabs.antd_page_router_20260615.show(runtime_context)
            -> selected page only
```

A tab switch reads the last published canonical generation. It does not invoke the Settings calculation transaction.

## Settings calculation and atomic publication

```text
Settings -> Run Calculation + Open Lunch
  -> core.settings_run_orchestrator_20260617.run_settings_calculation()
    -> existing protected calculations (unchanged formulas/weights/thresholds)
    -> completed-H1, priority, reliability and path outputs
    -> core.history_research_pipeline_20260620.build_history_research_transaction()
       [evidence only; no protected decision mutation]
    -> core.canonical_runtime_20260617.publish_canonical_atomically(...)
      -> services.canonical_snapshot_store.commit_snapshot(...)
        BEGIN IMMEDIATE
        -> canonical run/snapshot rows
        -> core.history_evidence_store_20260620.insert_history_bundle(...)
        -> status COMPLETED
        COMMIT
    -> publish one synchronized session-state generation
```

If evidence staging fails, the protected canonical result uses the existing fail-safe path and no mixed history generation is published.

## Lunch true-lazy graph

```text
Lunch default
  -> tabs.final_lunch_upgrade_20260617.render_lunch_quick_decision()
    -> ui.lunch_four_core_fields_20260619.render_lunch_six_core_fields()
      Field 1 toggle false -> no Full Metric history import/call
      Field 2 toggle false -> no Power BI renderer import/call
      Field 3 toggle false -> no regime history import/call
      Field 4-5 parent toggle false -> no 4A/4B import/call
      Field 6 toggle false -> no AI renderer import/call
```

When 4–5 is opened, one radio workspace is selected:

```text
4A -> Similar-Day + pattern + current canonical cards/priority/position/full metric
      + FIELD_4A evidence browser
4B -> regime summary + combined logic + Power BI regime projection
      + priority/decision/reliability/KNN/Greedy/advanced details
      + FIELD_4B evidence browser
```

4A and 4B retain independent render functions/state and read the same canonical generation. The former duplicate `_render_current_data` call was removed; “Original Data + Advanced Details” selects 4A instead of rendering another copy.

## Morning and Research

Morning now places a true toggle before `_home_ns()`; therefore `tabs.home` is not imported while closed. Research places a true toggle before importing `tabs.research`; Data Analysis, Data Mining and NLP are instantiated only for the selected/open workspace. Optional requests/NLP/Plotly/Polars/DuckDB code remains lazy.

## Disk-backed history/read path

```text
selected history field
  -> ui.history_evidence_browser_20260620
    -> projected query (selected columns only)
    -> LIMIT 48 phone / 120 desktop
    -> TinyLFU display cache (48 entries, 12 MB)
    -> st.dataframe bounded frame
    -> full CSV query/bytes only after Export button
```

Exact calculation histories remain in SQLite. M4 is applied only to display chart payloads; statistics and downloads use exact histories.
