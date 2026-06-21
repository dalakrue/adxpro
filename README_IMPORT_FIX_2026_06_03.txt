IMPORT FIX 2026-06-03
=====================

Fixed startup import error:
    cannot import name '_safe_rerun' from 'core.navigation_parts.state'

What changed:
1. core/navigation_parts/main.py now imports _safe_rerun from core.navigation_parts.timer.
2. core/navigation_parts/panels.py now imports _safe_rerun from core.navigation_parts.timer.
3. core/navigation_parts/state.py now keeps a compatibility _safe_rerun wrapper so older direct imports still work.

Why this is safe:
- No trading/reversal calculation logic was changed.
- Sidebar/tab UI files only received compatibility import fixes.
- Original core.navigation facade still exports _safe_rerun for older code.

Validation:
- Python compile check completed for core/, tabs/, main.py, and adx_dashpoard.py.

Run:
    pip install -r requirements.txt
    streamlit run main.py
