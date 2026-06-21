SIDEBAR OPEN / CLOSE FULL FIX - 2026-06-12

Fixed file:
- core/ui/styles.py

What was wrong:
- The previous hard-close sidebar patch could permanently hide the Streamlit sidebar.
- It used forced CSS and inline styles too aggressively.
- The native Streamlit open-sidebar button could not reliably restore the sidebar.
- Two close controls could appear while neither actually recovered the sidebar state.

What is fixed:
- Sidebar open button now releases all forced-close CSS before Streamlit opens it.
- Sidebar close button now closes normally and applies only a temporary visual close state.
- App buttons still auto-close the sidebar after click, matching the requested phone workflow.
- No original tab, ML logic, table, metric, chart, copy button, data calculation, or section was removed.

Safety:
- Patch is additive and limited to sidebar open/close behavior.
- Python syntax checked with compileall.
