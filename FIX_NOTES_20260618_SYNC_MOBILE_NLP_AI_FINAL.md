# Final Sync, Mobile, NLP and AI Repair — 2026-06-18

Base project: `3ba882dd-672f-4c06-892f-d39075e60a31.zip`

## Applied changes

- Added one post-publication operational synchronization layer. Every successful Settings calculation now mirrors the same run ID, generation, data signature and completed H1 candle to Lunch, Dinner, Finder, Research/AI, NLP, PowerBI, reliability, regime and Full Metric views without recalculating them.
- Added Settings **Synchronization Health** and **Errors / Fix Fast** panels. Renderer, runtime, connector and calculation errors are retained in a bounded, redacted ledger instead of being silently swallowed.
- Kept the protected Full Metric formulas untouched and retained the restored regime-history renderer directly inside Full Metric Details + History.
- Changed Finder into a read-only view of the published Lunch/Home generation. It no longer starts a separate prediction/history build and renders fewer phone rows.
- Enforced an honest rolling 10-day timestamp window for NLP news. Finnhub, persisted articles and public RSS are deduplicated; no fake rows are generated. Sparse real-news coverage and source/storage errors are displayed visibly.
- Added one shared 10-day news-mining result (topic impact, daily coverage and direction distribution) used by NLP, Data Mining, Lunch and Copy exports.
- Preserved the one Finnhub API-key input in Settings. NLP and the sidebar use status/actions only; no duplicate key field was added.
- Made prepared AI questions use their explicit intent. This prevents the 1,000-question library from collapsing many questions into one fuzzy answer. Interactive Dinner grounding now keeps the related local answer first and adds only question-relevant canonical evidence.
- Added next-1H and next-6H TP context, 6H less-risky bias and top mined-news topic to the existing Lunch quick evidence.
- Rebuilt Copy Short as a decision-first pack capped at 5,800 characters, emphasizing next-1H/6H TP context, less-risky 6H bias, Full Metric scores, regime, reliability, NLP rank 1 and top two opportunities. Copy Full now also includes shared news-mining and sync status.
- Reduced mobile DOM/render load: phone table views use 72 rows, Dinner limits redundant deep tables, decorative theme stacks/animations/popups are skipped in phone mode, and cached calculation objects are reused instead of copied where possible.
- Reduced the three-dot popover to 230 px on laptop and 205 px on phone. Removed large download/manual fallback controls from inside the popover while retaining the real copy actions.
- Fixed phone `st.metric` clipping using compact 76 px cards, responsive values, wrapping labels and narrower sidebar sizing for iPhone-class screens.
- Fixed lightweight/test-environment NLP imports and Streamlit cache decorator fallbacks.

## Protected logic

`tabs/eurusd_h1_matrix.py` remains byte-for-byte unchanged.
SHA-256: `fe0797ab30f469f3ea748bc66a690b18a68aaf91306ac33c797bdcdcf6e60682`

## Validation

- Python compileall: PASS
- Pytest: **89 passed**
- Architecture validator: PASS
- Final synchronization validator: PASS
- Finnhub/NLP/Lunch/Research validator: PASS
- Main entry point: `streamlit run app.py`

A live browser/phone smoke test was not available in the execution container because Streamlit itself is not installed there; the project keeps `streamlit>=1.35` in `requirements.txt` for its target runtime.
