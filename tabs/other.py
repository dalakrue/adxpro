"""V24 lazy Other tab.

Engine, Train Data, Database, Pre Original, and Profile live here as inner
buttons. Nothing heavy is imported or rendered until the user presses the
manual Run Calculate button.
"""

import streamlit as st

try:
    from core.global_upgrade import render_page_shell, render_tab_footer
except Exception:
    def render_page_shell(title, subtitle="", icon=""):
        st.markdown(f"# {icon} {title}")
        if subtitle:
            st.caption(subtitle)
    def render_tab_footer(title):
        return None


INNER_TABS = [
    ("Engine", "⚡", "tabs.engine"),
    ("Train Data", "🧠", "tabs.train_data"),
    ("Database", "🗄️", "tabs.database_tab"),
    ("Pre Original", "🧾", "tabs.pre_original"),
    ("Profile", "👤", "tabs.profile"),
]


def _choose_inner_tab():
    current = st.session_state.get("other_inner_tab", "Engine")
    names = [name for name, _, _ in INNER_TABS]
    if current not in names:
        current = "Engine"
        st.session_state.other_inner_tab = current

    cols = st.columns(len(INNER_TABS))
    for idx, (name, icon, _module) in enumerate(INNER_TABS):
        with cols[idx]:
            label = f"✅ {icon} {name}" if current == name else f"{icon} {name}"
            if st.button(label, use_container_width=True, key=f"other_inner_tab_{idx}"):
                st.session_state.other_inner_tab = name
                current = name
    return st.session_state.get("other_inner_tab", current)


def _render_inner_page(name: str):
    module_map = {name: module for name, _icon, module in INNER_TABS}
    module_name = module_map.get(name)
    if not module_name:
        st.warning("Unknown inner tab.")
        return
    try:
        import importlib
        mod = importlib.import_module(module_name)
        show = getattr(mod, "show")
        return show()
    except Exception as exc:
        st.error(f"{name} inner tab could not run safely.")
        with st.expander(f"Show {name} error", expanded=True):
            st.exception(exc)


def show():
    render_page_shell(
        "Other",
        "Lazy inner workspace. Press Run Calculate first; otherwise Engine, Train Data, Database, Pre Original, and Profile do not run.",
        "📂",
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("▶ Run Calculate — Enable Other Inner Tabs", use_container_width=True, key="other_run_calculate_button"):
            st.session_state["other_run_calculate"] = True
            st.success("Other workspace calculation is enabled. Choose an inner tab below.")
    with c2:
        if st.button("⏸ Stop / Lock", use_container_width=True, key="other_stop_calculate_button"):
            st.session_state["other_run_calculate"] = False
            st.info("Other workspace is locked. Inner tabs will not run.")

    st.caption(
        "Manual gate active: hidden inner tabs are not calculated. Only the selected inner tab renders after Run Calculate is pressed."
    )

    selected = _choose_inner_tab()

    if not bool(st.session_state.get("other_run_calculate", False)):
        with st.expander("📂 Open / Close — Other tab is waiting", expanded=True):
            st.info(
                "Press **Run Calculate** first. Until then, Engine, Train Data, Database, Pre Original, and Profile stay idle to reduce RAM and avoid auto-run."
            )
        render_tab_footer("Other")
        return

    st.markdown(f"### Running inner tab: {selected}")
    _render_inner_page(selected)
    render_tab_footer("Other")


# 2026-06-14 Logic Safety Guard + Hidden Danger Engine for Other/Dinner-regime workspace.
try:
    from ui.logic_safety_panel import install as _install_logic_safety_panel_other_20260614
    _install_logic_safety_panel_other_20260614(globals(), location="Other/Dinner-Regime")
    del _install_logic_safety_panel_other_20260614
except Exception as _logic_safety_panel_other_exc_20260614:
    try:
        import streamlit as st
        st.warning(f"Logic Safety Guard wrapper skipped: {_logic_safety_panel_other_exc_20260614}")
    except Exception:
        pass
