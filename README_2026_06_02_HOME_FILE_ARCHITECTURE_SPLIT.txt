HOME FILE ARCHITECTURE SPLIT - 2026-06-02
============================================================

Goal:
- Split Home-related large files into smaller architecture pieces.
- Keep original Home behavior unchanged.
- Make future Home CSS, UIUX, phone layout, glass effect, and metric upgrades easier.

Main changes:
1) tabs/home_split/legacy/implementation.py
   - Changed from one huge Home implementation file into a small compatibility loader.
   - Original source is preserved in:
     tabs/home_split/legacy/implementation_parts/part_01.py ... part_06.py

2) tabs/home_split/doo_prime_deep.py
   - Changed from one huge Doo Prime Home deep-analysis file into a small compatibility loader.
   - Original source is preserved in:
     tabs/home_split/doo_prime_deep_parts/part_01.py ... part_06.py

3) data/home_split_package/home_split/implementation.py
   - Split the duplicate Home package implementation into smaller parts too.

4) New future-upgrade files:
   - tabs/home_split/css_hooks.py
   - tabs/home_split/uiux_hooks.py
   - tabs/home_split/architecture.py

Why this is safer:
- Existing import paths still work.
- tabs/home.py still calls tabs.home_split.home.show().
- tabs/home_split/implementation.py still exposes the legacy functions.
- No original formulas, metrics, reversal logic, risk logic, or Doo Prime logic were intentionally changed.

Validation:
- Python compile check passed with: python -m compileall -q .

Future upgrade rule:
- For new Home CSS/UIUX: edit css_hooks.py or uiux_hooks.py first.
- For new Home metric panels: create a new small module under tabs/home_split/ instead of adding more code to the legacy loader.
- Avoid editing part_XX.py manually unless you are replacing the preserved original logic.
