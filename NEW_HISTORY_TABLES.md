# New History Tables

| table | grain | business key | packaged rows | status |
|---|---|---|---|---|
| source_freshness_history | one source per canonical generation | calculation_id + source | 0 | Created; populated only by a valid future Settings publication |
| schema_drift_history | one column/rule violation per generation | calculation_id + column_name + rule_id | 0 | Created; populated only by a valid future Settings publication |
| candle_integrity_history | one integrity issue type per generation | calculation_id + issue_type | 0 | Created; populated only by a valid future Settings publication |
| data_lint_history | one lightweight lint rule per generation | calculation_id + rule_id + column_name | 0 | Created; populated only by a valid future Settings publication |
| revision_lineage_history | one revised candle field | candle_timestamp + field_name + detected_at | 0 | Created; populated only by a valid future Settings publication |
| cleaning_impact_history | one proposed cleaning rule per chronological evaluation | cleaning_rule + evaluation_window + calculation_id | 0 | Created; populated only by a valid future Settings publication |
| incremental_refresh_history | one processing stage per canonical generation | calculation_id + processing_stage | 0 | Created; populated only by a valid future Settings publication |
| mobile_render_budget_history | one renderer invocation per device profile and generation | calculation_id + viewport_profile + field_name + created_at | 0 | Created; populated only by a valid future Settings publication |
| approximate_preview_audit_history | one approximate noncanonical preview query | calculation_id + query_name + created_at | 0 | Created; populated only by a valid future Settings publication |

All nine tables are additive and idempotent. Zero rows are displayed as **INSUFFICIENT EVIDENCE**, never as proof. `cleaning_impact_history` stays SHADOW, and `approximate_preview_audit_history` cannot influence canonical outputs.
