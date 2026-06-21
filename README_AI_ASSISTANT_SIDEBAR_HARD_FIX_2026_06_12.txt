AI ASSISTANT + SIDEBAR HARD FIX — 2026-06-12

What was fixed/upgraded:

1) Sidebar auto-close hard patch
- Added global sidebar hard-close JS/CSS override in core/ui/styles.py.
- Sidebar now auto-closes after app buttons, sidebar buttons, tab buttons, run buttons, copy buttons, connect/disconnect buttons, and mobile taps.
- It also hides Streamlit's leftover sidebar sliver/overlay when collapsed.
- Keeps the Open Sidebar control usable by releasing the forced-close style when the open-control itself is tapped.

2) AI Assistant Lite smart input upgrade
- Added a large phone-friendly Smart Text Input box above the Question Box.
- Added one main Analyze Smart Text button.
- Added live recognition preview showing interpreted intent, match %, strength, side, and normalized text.
- Kept the compact one-dropdown Question Box with 203 prepared local questions.
- Kept the bottom chat input as backup.

3) NLP recognition improvement
- Improved typo/grammar normalization for common phone typing mistakes.
- Improved similarity matching using sequence similarity + token-sort + token-set + overlap scoring.
- Improved recognition for sell/buy entry prices, TP questions, within-next-hours questions, history matching, predictive/prescriptive analysis, and confidence/quality checks.

Safety:
- No OpenAI API was added.
- No paid API was added.
- No new ML model was added.
- Existing logic/calculation sections were not removed.
- Syntax check passed with python compileall.
