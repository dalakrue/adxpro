# Evidence and Limitations

## Verified
- 458 packaged Python files parse/compile.
- Streamlit starts with `streamlit run app.py`; the health endpoint returned `ok`.
- New unit/invariant tests cover schema, common contract, idempotency, rollback, payload bounds, exactly one publication call, and closed-field no-execution.
- All four SQLite databases return `PRAGMA integrity_check = ok`.
- The nine pre-existing stored canonical snapshot rows are byte-identical to the untouched recovered database.
- New schemas are additive and zero-row tables remain labelled INSUFFICIENT EVIDENCE.

## Critical recovery limitation
The user-supplied ZIP is truncated. It yielded 317 intact entries, although its manifest lists 924. A public initial repository commit was used to restore an older base before overlaying recovered files. 230 manifest files remain unavailable and 62 expected files do not match their listed latest hashes. Therefore this package is a runnable, tested best-effort reconstruction—not a guaranteed complete latest original.

## Not claimed
- No full protected Settings calculation was executed against a verified latest source tree.
- No new BUY/SELL/WAIT output hash was compared; only existing stored snapshot rows were proven unchanged.
- The full 12-scenario browser benchmark and real iPhone 11 Pro screenshots were not available.
- The 30% target is not claimed for the full application. Only isolated SQL/history workloads show reductions above 30% and 50%.
- Existing tests missing from the truncated upload could not be rerun; newly added tests pass.
- New quality tables have zero packaged evidence rows because no valid post-upgrade Settings publication was fabricated.
- ActiveClean/CleanML promotion remains SHADOW with no accuracy claim.
