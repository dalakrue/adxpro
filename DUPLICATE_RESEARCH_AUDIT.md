# Duplicate Research Audit

Created before additive integration decisions. “REUSE” keeps the existing authority; “UPGRADE” adds evidence or display constraints without a parallel engine.

| paper_title | existing_file | existing_function | existing_table | current_status | duplicate_risk | reuse_or_upgrade_decision |
|---|---|---|---|---|---|---|
| Data Validation for Machine Learning | core/canonical_data_validation_20260621.py | validate_source_frame; validate_canonical_payload | data_quality_generation; data_quality_constraint_result; data_quality_metric_history | ACTIVE preflight + prepublication gate | HIGH | REUSE existing authority; add source/schema/integrity evidence rows only |
| Automating Large-Scale Data Quality Verification | core/declarative_data_quality_20260621.py | evaluate_constraints; shared_frame_aggregates | data_quality_constraint_result; source_freshness_history; schema_drift_history | ACTIVE declarative constraints | HIGH | UPGRADE persistence and single-pass aggregates; no second rule engine |
| The Data Linter: Lightweight, Automated Sanity Checking for ML Data Sets | core/history_quality_store_20260621.py | build_quality_history_bundle | data_lint_history | ADDITIVE lightweight lints | MEDIUM | UPGRADE existing checks with bounded constant/copied/missing/volume evidence |
| ActiveClean: Interactive Data Cleaning For Statistical Modeling | core/history_quality_store_20260621.py | SHADOW schema only | cleaning_impact_history | SHADOW / no rows | HIGH | REJECT automatic cleaning; keep proposed rules SHADOW until chronological approval |
| CleanML: A Study for Evaluating the Impact of Data Cleaning on ML Classification Tasks | core/history_quality_store_20260621.py | SHADOW schema only | cleaning_impact_history | SHADOW / no rows | HIGH | REUSE same SHADOW evaluation ledger; require accuracy plus coverage and two windows |
| Differential Dataflow | core/research_validation_store_20260621.py; core/history_quality_store_20260621.py | delta maintenance state; incremental refresh evidence | delta_maintenance_history; exact_delta_state; incremental_refresh_history | Existing delta audit plus additive stage metrics | HIGH | REUSE existing delta authority; do not introduce another computation engine |
| The Design and Implementation of Modern Column-Oriented Database Systems | core/history_evidence_store_20260620.py; core/history_columnar_archive_20260620.py | query_history; archive helpers | history tables + archive metadata | Existing SQLite; column projection upgraded in active browser | MEDIUM | REUSE SQLite, explicit projections, bounded rows; defer DuckDB/Parquet threshold promotion |
| BlinkDB: Queries with Bounded Errors and Bounded Response Times on Very Large Data | core/history_quality_store_20260621.py | schema/audit only | approximate_preview_audit_history | NONCANONICAL preview audit; no rows | HIGH | REJECT approximation for canonical/protected/export; allow audited preview only |
| Falcon: Balancing Interactive Latency and Resolution Sensitivity for Scalable Linked Visualizations | ui/lunch_four_core_fields_20260619.py | render_lunch_six_core_fields; true load gates | mobile_render_budget_history | ACTIVE progressive field loading | LOW | UPGRADE renderer gates, bounded initial rows, exact export on explicit action |
| Mobile Web Browsing under Memory Pressure | ui/mobile_low_heat_20260617.py; ui/lunch_four_core_fields_20260619.py | apply_mobile_low_heat_css; _bounded; _record_budget | mobile_render_budget_history | ACTIVE mobile budget safeguards | LOW | UPGRADE one-column/overflow/touch targets and bounded projections |

## Source foundations
- Breck et al., *Data Validation for Machine Learning* (MLSys 2019).
- Schelter et al., *Automating Large-Scale Data Quality Verification* (PVLDB 2018).
- Hynes, Sculley, Terry, *The Data Linter* (2017).
- Krishnan et al., *ActiveClean* (SIGMOD 2016).
- Li et al., *CleanML* (ICDE 2021).
- McSherry et al., *Differential Dataflow* (CIDR 2013).
- Abadi et al., *The Design and Implementation of Modern Column-Oriented Database Systems*.
- Agarwal et al., *BlinkDB*.
- Moritz, Howe, Heer, *Falcon* (CHI 2019).
- Qazi et al., *Mobile Web Browsing Under Memory Pressure* (CCR 2020).
