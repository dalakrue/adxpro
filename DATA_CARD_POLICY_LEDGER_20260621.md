# Data Card — Policy Decision Ledger

- Grain: one `decision_id × fixed evaluation_horizon × record_version` row.
- Horizons: 1H, 2H, 3H and 6H, stored and settled separately.
- Key: `record_key`; latest logical record selected by `(decision_id, evaluation_horizon, max(record_version))`.
- Instrument/timeframe: EURUSD/H1 only. M1 is not an outcome horizon and may remain confirmation-only in the protected engine.
- Timing: all feature/context values are captured at decision cutoff. Outcome settlement requires a completed candle at or after the fixed target.
- Costs: spread, slippage and commission must be explicit. Missing costs produce `SETTLED_COST_INCOMPLETE`, excluded from OPE/tail evidence.
- Probabilities: only explicit behavior/candidate vectors are accepted. Missing values remain NULL and make OPE non-identifiable.
- Retention: promotion reads all valid settled rows; the 25-day UI limit is display-only.
- Privacy/secrets: no external API or LLM data is sent.
