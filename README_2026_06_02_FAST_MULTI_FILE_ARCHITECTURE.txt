FAST MULTI-FILE ARCHITECTURE UPGRADE — 2026-06-02

Run:
    streamlit run main.py

Main changes:
1. Divided core/common.py into smaller architecture files:
   - core/config/defaults.py
   - core/state/session_state.py
   - core/utils/numeric.py
   - core/utils/timer.py
   - core/utils/symbols.py
   - core/data/synthetic.py

2. Kept core/common.py as a compatibility facade so old imports still work.

3. Added core/app/imports.py and updated core/app/routes.py for cached lazy tab import.

4. Moved Train Data heavy implementation into:
   - tabs/train/train_data_legacy.py
   Root tabs/train_data.py is now only a safe wrapper.

5. Isolated heavy preserved Home and Account implementations under:
   - tabs/home_split/legacy/implementation.py
   - tabs/account_split/legacy/implementation.py
   Existing implementation.py files remain compatibility facades.

6. Added short connector hot-cache protection in core/connectors/data_connectors.py.
   This prevents duplicate MT5/TwelveData/Bridge calls during the same Streamlit rerun/navigation action.

7. Added architecture guide:
   - docs/architecture/FAST_MULTI_FILE_ARCHITECTURE_2026_06_02.md

8. Added local validation script:
   - python tools/validate_architecture.py

This upgrade is designed for faster file transition, easier future upgrades, safer new feature adding, and lower risk of breaking original tab behavior.
