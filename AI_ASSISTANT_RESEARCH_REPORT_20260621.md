# AI Assistant and Performance Research Implementation Report

The implementation adopts engineering concepts, not paper-level guarantees. No paper changes the protected market calculations or creates a new decision engine.

## 1. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

- **Authors/year:** Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kiela (2020).
- **Concept adopted:** retrieve compact non-parametric evidence before drafting an answer.
- **Core hypothesis:** generation grounded in explicit retrieved evidence can be more factual and attributable than parametric-only generation.
- **Formal theorem adopted:** none; the paper is used as an empirical architecture reference.
- **Assumptions:** compact evidence records are correctly tied to a completed generation and settled evidence.
- **Implemented:** local source registry, lexical/metadata retrieval, bounded top-k evidence, source labels.
- **Not implemented:** dense Wikipedia index, neural retriever, seq2seq fine-tuning, token-level latent retrieval.
- **Guarantee boundary:** retrieval can expose evidence but cannot guarantee market truth or forecast success.
- **Resource cost:** O(N) lexical scoring over a bounded registry, normally 4–8 retained records.
- **Status:** production read-only assistant path.
- **Validation:** tests verify generation identity, evidence status, and insufficient-evidence behavior.

## 2. ReAct: Synergizing Reasoning and Acting in Language Models

- **Authors/year:** Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao (2022 preprint; ICLR 2023).
- **Concept adopted:** controlled intent-to-read-only-action routing.
- **Core hypothesis:** interleaving planning with environment actions can improve grounded task completion.
- **Formal theorem adopted:** none.
- **Assumptions:** the allowed action registry is closed and read-only.
- **Implemented:** intent detection, required-source selection, read-only calculation selection, freshness/conflict checks.
- **Not implemented:** free-form tool use, autonomous environment mutation, hidden chain-of-thought display.
- **Guarantee boundary:** routing constrains actions; it does not prove answer correctness.
- **Resource cost:** one deterministic route and one bounded retrieval pass.
- **Status:** production, read-only.
- **Validation:** tests prove AI does not change protected decision fields.

## 3. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

- **Authors/year:** Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi (2023).
- **Concept adopted:** evidence coverage/status criticism after drafting.
- **Core hypothesis:** deciding when retrieval is needed and critiquing retrieved support can improve factuality.
- **Formal theorem adopted:** none.
- **Assumptions:** required source classes and evidence status metadata are meaningful.
- **Implemented:** evidence critic with SUPPORTED, PARTIALLY_SUPPORTED, CONFLICTING_EVIDENCE, INSUFFICIENT_EVIDENCE, and STALE_GENERATION.
- **Not implemented:** training reflection tokens or Self-RAG model weights.
- **Guarantee boundary:** status is a deterministic support classification, not a proof.
- **Resource cost:** one bounded critic pass.
- **Status:** production.
- **Validation:** missing data returns INSUFFICIENT_EVIDENCE.

## 4. Self-Refine: Iterative Refinement with Self-Feedback

- **Authors/year:** Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank Gupta, Bodhisattwa Prasad Majumder, Katherine Hermann, Sean Welleck, Amir Yazdanbakhsh, Peter Clark (2023).
- **Concept adopted:** one feedback-driven revision pass.
- **Core hypothesis:** feedback on an initial output can improve the final output without retraining.
- **Formal theorem adopted:** none.
- **Assumptions:** critic rules detect missing identity, evidence, freshness, conflict, and limitations fields.
- **Implemented:** draft → critic → exactly one revision.
- **Not implemented:** open-ended iteration or LLM self-training.
- **Guarantee boundary:** one pass limits cost but may not resolve every ambiguity.
- **Resource cost:** fixed bounded pass.
- **Status:** production.
- **Validation:** final answer structure tests.

## 5. Lost in the Middle: How Language Models Use Long Contexts

- **Authors/year:** Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang (2023).
- **Concept adopted:** order high-value identity and decisive evidence at context boundaries instead of burying them.
- **Core hypothesis:** relevant information placed in the middle of long contexts can be used less reliably.
- **Formal theorem adopted:** none; empirical observation.
- **Assumptions:** evidence relevance scores are adequate for ordering.
- **Implemented:** identity first, strongest support/conflict near beginning/end, compact bounded context.
- **Not implemented:** long-context model experiments.
- **Guarantee boundary:** ordering reduces exposure to context-position risk but cannot eliminate it.
- **Resource cost:** O(k log k) ordering for small k.
- **Status:** production.
- **Validation:** bounded 4–8 record retrieval and answer-size tests.

## 6. FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance

- **Authors/year:** Lingjiao Chen, Matei Zaharia, James Zou (2023 preprint; ICLR 2024).
- **Concept adopted:** complexity-aware routing and strict resource budgets.
- **Core hypothesis:** query-dependent routing/cascades can reduce cost while preserving useful quality.
- **Formal theorem adopted:** none.
- **Assumptions:** lexical local responses are sufficient for this read-only explanation task.
- **Implemented:** simple/complex budget selection, bounded source registry, top-k and answer-character caps.
- **Not implemented:** paid LLM cascade or learned router.
- **Guarantee boundary:** resource savings are measured locally; no claimed 98% cost result is transferred to this app.
- **Resource cost:** bounded local CPU/RAM only.
- **Status:** production.
- **Validation:** headless simple/complex AI benchmark and cache bounds.

## 7. On Calibration of Modern Neural Networks

- **Authors/year:** Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger (2017).
- **Concept adopted:** separate support confidence from raw model/decision scores and penalize stale/conflicting/low-coverage answers.
- **Core hypothesis:** predictive confidence may be miscalibrated and should be calibrated independently.
- **Formal theorem adopted:** none; empirical calibration reference.
- **Assumptions:** evidence coverage/reliability/freshness are valid inputs to a support-confidence heuristic.
- **Implemented:** deterministic calibrated evidence confidence with explicit limitations.
- **Not implemented:** neural-network temperature scaling training.
- **Guarantee boundary:** confidence describes answer support, not trade win probability.
- **Resource cost:** constant-time aggregation over retrieved records.
- **Status:** production support metric.
- **Validation:** bounded confidence and stale/conflict penalties.

## 8. DuckDB: an Embeddable Analytical Database

- **Authors/year:** Mark Raasveldt, Hannes Mühleisen (2019).
- **Concept adopted:** embedded analytical queries with projection, predicates, ordering, and limit pushdown.
- **Core hypothesis:** an embedded OLAP database can efficiently serve analytical workloads inside applications.
- **Formal theorem adopted:** none; systems paper.
- **Assumptions:** DuckDB is installed and the DataFrame schema can be registered safely.
- **Implemented:** selected-column completed-H1 25-day queries with bounded rows; vectorized fallback.
- **Not implemented:** a new database authority or migration of protected history logic.
- **Guarantee boundary:** improves query shape; performance depends on data size and environment.
- **Resource cost:** one bounded in-process query.
- **Status:** production with pandas fallback.
- **Validation:** ordering/future-row tests and headless memory benchmark.

## 9. MonetDB/X100: Hyper-Pipelining Query Execution

- **Authors/year:** Peter Boncz, Marcin Zukowski, Niels Nes (2005).
- **Concept adopted:** column-oriented, vectorized processing over selected blocks rather than Python row loops.
- **Core hypothesis:** vectorized cache-conscious execution can improve analytical CPU efficiency.
- **Formal theorem adopted:** none; systems design and empirical evaluation.
- **Assumptions:** operations can be expressed in vectorized pandas/NumPy/DuckDB form.
- **Implemented:** projection-first query, vectorized filters/sorts, shallow views, no new `iterrows` in added code.
- **Not implemented:** X100 execution engine, SIMD kernels, or storage format.
- **Guarantee boundary:** design inspiration only; no X100 speedup claim is made.
- **Resource cost:** reduced temporary-column footprint; query latency may be slightly higher on tiny fixtures.
- **Status:** production engineering pattern.
- **Validation:** memory allocation decreased in the Field 3 query fixture.

## 10. ARC: A Self-Tuning, Low Overhead Replacement Cache

- **Authors/year:** Nimrod Megiddo, Dharmendra S. Modha (2003).
- **Concept adopted:** balance recency and frequency under a strict cache budget.
- **Core hypothesis:** adaptive recency/frequency replacement can outperform fixed one-dimensional policies across changing workloads.
- **Formal theorem adopted:** none in this implementation; the literal ARC algorithm and its analytical properties are not reproduced.
- **Assumptions:** presentation objects are reconstructable and safe to evict.
- **Implemented:** bounded session-local recency/frequency-aware presentation cache with item/byte limits.
- **Not implemented:** literal ARC T1/T2/B1/B2 lists or storage-page replacement.
- **Guarantee boundary:** ARC-inspired heuristic only.
- **Resource cost:** O(cache-size) eviction over at most 32 entries.
- **Status:** production presentation cache.
- **Validation:** Reduce RAM preserves canonical/settled data and clears reconstructable entries.
