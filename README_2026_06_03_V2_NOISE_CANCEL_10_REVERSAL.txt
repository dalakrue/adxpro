2026-06-03 V2 NOISE-CANCEL 10 REVERSAL UPGRADE
================================================

Purpose
-------
This patch upgrades the 10 Reversal Decision used by BOTH:
1. Home tab Reversal Early Warning Engine
2. Finder inner tab day replay / 7-of-10 history scan

Main improvement
----------------
The previous strict gate could still promote some transition-only clusters too high.
This v2 patch keeps the original code structure intact but tightens the final gate:

7/10 danger now requires:
- trend exhaustion
- pressure transfer
- shock move confirmation
- clean context / not duplicate-sparse noise

Transition-only setup now stays as:
- 6/10 WATCH / transition warning
instead of becoming full 7/10 danger.

New noise blockers
------------------
The engine now tracks and blocks:
- micro_chop_noise
- no_pressure_reversal
- continuation_not_reversal
- weak_model_noise
- duplicate_or_sparse_noise
- strict_noise_block

New table fields
----------------
Home 25D scan and Finder day scan now show:
- strict_noise_block
- transition_warning
- structure_quality_score
- micro_chop_noise
- continuation_not_reversal

Edited files
------------
- tabs/home_split/reversal_engine_full_correct_patch.py
- tabs/home_split/home_finder_reversal_history_upgrade.py

Validation
----------
All Python files were compile-tested with compileall successfully.

How to run
----------
streamlit run main.py

