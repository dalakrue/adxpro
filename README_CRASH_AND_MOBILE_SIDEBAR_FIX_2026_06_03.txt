CRASH + MOBILE SIDEBAR CLOSE FIX - 2026-06-03
================================================

Fixed:
1) SyntaxError from Git conflict marker in core/app/runner.py path.
   - Verified all Python files parse with ast.parse.
   - Verified no Python file contains <<<<<<< or >>>>>>> conflict markers.

2) Mobile sidebar close button not fully closing.
   - Upgraded core/ui/legacy_impl/styles_impl.py:
     auto_close_sidebar_script()
     request_close_sidebar()
   - New closer tries multiple Streamlit sidebar close selectors.
   - Adds mobile fallback hide only when normal close click fails.
   - Keeps original navigation/data/app logic unchanged.

Validation performed:
- python -m compileall -q .  PASSED
- AST parse all .py files     PASSED
- Conflict marker scan        PASSED

Run:
streamlit run adx_dashpoard.py

If port busy:
streamlit run adx_dashpoard.py --server.port 8502
