# Evidence and Limitations

## What is directly verified

- Mechanisms for all ten requested papers are present.
- Protected canonical decision fields are unchanged by the transaction.
- Shadow direction cannot reverse BUY↔SELL and cannot promote WAIT.
- All outputs are bounded and tied to one source generation.
- Database rows are idempotent and participate in canonical atomic publication.
- All 296 collected tests passed in controlled groups.
- All active Python files compile.
- Streamlit health endpoint returned `ok` for `app.py`.
- Migration/verification/rollback paths passed on temporary databases.

## What is synthetic verification

The new focused tests and performance benchmark use deterministic synthetic H1 and settled-forecast evidence. They verify software invariants and numerical behavior, not market effectiveness.

## What historical evidence is available

The runtime can evaluate real settled rows already held in the existing trust/history stores. This delivery does not claim that the supplied database contains enough independent settled observations for every theorem or gate. The transaction will publish exact support counts and INSUFFICIENT_EVIDENCE where needed.

## What is not verified

- improved forecast accuracy;
- improved profitability or lower trading loss;
- theorem-level Model-X FDR control;
- theorem-level online FDR/FDP control under the actual dependence structure;
- globally monotonic production behavior;
- lower total CPU/RAM use;
- causal effect of any feature;
- future regime robustness.

## Production influence

Production influence is hard-disabled in this delivery. Passing synthetic tests does not promote a method. Real promotion would require all gates in two independent chronological windows, an explicit reviewed enablement change, and rollback evidence.
