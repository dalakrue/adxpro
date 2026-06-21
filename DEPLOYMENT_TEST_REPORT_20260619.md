# Deployment test report — 2026-06-19

## Root cause verified

The cloud log reports Python 3.14.6. The previous requirement `numpy>=1.26,<2.3`
selects NumPy 2.2.6 for Python 3.14. That release has no Python 3.14 Linux wheel,
so `uv` must compile NumPy from source after displaying `Resolved 85 packages`.
This explains the multi-hour stall.

## Fix

- Python below 3.14 keeps NumPy `>=1.26,<2.3`.
- Python 3.14 and newer uses NumPy `>=2.3,<2.4`, which resolves to a binary wheel.
- Added `.python-version` requesting Python 3.12 for compatible local tooling.
- Preserved all existing application dependencies and trading logic.

## Validation completed

- All Python files: `compileall` passed.
- Clean dependency installation on Python 3.13.5: passed; 85 packages installed.
- Installation elapsed time in the test environment: 16.67 seconds.
- Required and optional imports: passed.
- Streamlit start using `adx_dashpoard.py`: passed.
- Streamlit health endpoint: returned `ok`.
- Cloud/architecture/settings/UI focused tests: 27 passed.
- Python 3.14 Linux resolution: NumPy 2.3.5 wheel selected; no NumPy source build.

The complete model/research suite contains long-running statistical tests and did
not finish inside the isolated execution limit. No failure was observed before
the limit; deployment-critical checks were run separately and passed.
