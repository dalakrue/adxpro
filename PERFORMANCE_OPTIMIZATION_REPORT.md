# Performance Optimization Report

| scenario | before wall ms | after wall ms | wall reduction | before CPU ms | after CPU ms | CPU reduction | before Python peak | after Python peak | Python peak reduction |
|---|---|---|---|---|---|---|---|---|---|
| Open Field 1 history | 2394.917 | 61.447 | 97.43% | 2260.000 | 60.000 | 97.35% | 71,469,749 | 30,328 | 99.96% |
| Search history | 486.351 | 62.703 | 87.11% | 460.000 | 60.000 | 86.96% | 42,126,754 | 23,541 | 99.94% |
| Page history | 633.175 | 74.182 | 88.28% | 600.000 | 70.000 | 88.33% | 42,126,334 | 23,628 | 99.94% |

## Measured contributions
- SQL projection, server-side filtering, ordering and limit; no active-path `SELECT *` in the new browser.
- Lazy JSON: row payloads are not decoded for initial lists.
- True field gates: AppTest recorded zero query/row construction with all fields closed.
- Bounded mobile projection: 50 initial rows and deferred exact export.
- Single-pass quality aggregates: the 5,000-row evidence stage is reported separately and does not include protected calculation cost.

## Target determination
The synthetic history-query workloads exceed the 30% and 50% targets. **The full application target is NOT VERIFIED and therefore is not claimed achieved.** A valid before/after run of the complete latest protected engine, browser fields, clipboard/export transfer, and iPhone/laptop screenshots could not be produced because the uploaded ZIP is truncated. Cold startup is reported only for the reconstructed after-build and has no comparable latest baseline.
