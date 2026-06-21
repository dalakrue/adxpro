# Evidence and Limitations

## Evidence produced

- Full source inventory and call-path inspection.
- Protected file SHA-256 comparison.
- Exactly-six-field static and behavioral tests.
- Refresh-without-calculation tests.
- Copy budget/parity tests.
- AI support-status/generation tests.
- Completed-H1 and future-row rejection tests.
- Compile/import/startup contract tests.
- Headless before/after benchmark with raw JSON measurements.

## Limitations

1. The audit container did not include a live Streamlit server/browser at the start, so browser paint, iPhone thermal behavior, and actual cloud rerun latency were not measured.
2. Live Refresh Data latency was not measured against a real credentialed connector; the benchmark injects a connector fixture through the public refresh path.
3. The protected Run Calculation was not benchmarked with live data because doing so would require credentials and a production-equivalent environment. Regression tests and hashes validate its unchanged source boundary.
4. The local AI assistant is a deterministic evidence summarizer/planner, not a general-purpose language model. It may return PARTIALLY_SUPPORTED or INSUFFICIENT_EVIDENCE instead of producing fluent unsupported claims.
5. Confidence is evidence-support confidence, not market-success probability.
6. DuckDB improves bounded analytical query shape, but tiny DataFrames can be faster with pandas; the implementation has a vectorized fallback.
7. Existing databases may require normal project migrations already documented by the original package. This upgrade adds no schema migration.
8. Compatibility aliases/comments remain for older tests and imports; they do not restore the previous Field 5/6 nesting.

## Unsupported claims warning

No performance percentage, profitability, forecast accuracy, risk outcome, or production thermal reduction is guaranteed. Only measured values in the included environment are reported.
