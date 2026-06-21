"""Stable main-page menu replacing native-sidebar dependency (2026-06-15).

The app can be fully navigated and controlled from this expander even if the
native Streamlit sidebar is closed, hidden, or unavailable.
"""
from __future__ import annotations

import time
import streamlit as st


def _safe_rerun() -> None:
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def _soft_menu_css() -> None:
    st.markdown(
        """
<style id="new7-main-page-menu-antd-20260615">
.new7-card{
  border:1px solid rgba(99,102,241,.13);
  border-radius:20px;
  padding:11px 12px;
  margin:.20rem 0 .55rem 0;
  background:linear-gradient(135deg,rgba(255,255,255,.83),rgba(239,246,255,.68));
  box-shadow:0 10px 26px rgba(15,23,42,.055);
}
.new7-menu-note{font-size:.76rem;color:#64748b;line-height:1.28;}
@media(max-width:430px){
  .new7-card{border-radius:16px;padding:9px 10px;margin:.15rem 0 .42rem 0;box-shadow:0 6px 14px rgba(15,23,42,.045);} 
  div[data-testid="stExpander"] details{border-radius:16px!important;}
  div[data-testid="stButton"] button{min-height:38px!important;font-size:.78rem!important;padding:.18rem .35rem!important;}
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _sync_status() -> None:
    try:
        from ui.antd_navigation_20260615 import render_active_nav_status
        render_active_nav_status()
    except Exception:
        page = st.session_state.get("active_page", "Home")
        sub = st.session_state.get("active_subpage", "")
        st.caption(f"Active page: {page} | Subpage: {sub or 'Main'}")


def _render_quick_actions() -> None:
    st.markdown("#### ⚡ Quick Controls")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("▶ Run Calculation", key="main_menu_run_calculation_20260615", use_container_width=True):
        st.session_state["metric_run_calculate"] = True
        st.session_state["research_run_calculate"] = True
        st.session_state["other_run_calculate"] = True
        st.session_state["ui_navigation_click_ts"] = time.time()
        _safe_rerun()
    if c2.button("📋 Copy Short", key="main_menu_copy_short_hint_20260615", use_container_width=True):
        st.session_state["main_menu_copy_hint_20260615"] = "Copy Short is preserved inside the active calculation section. Open the active page and use its original Copy Short button."
    if c3.button("📋 Copy Full", key="main_menu_copy_full_hint_20260615", use_container_width=True):
        st.session_state["main_menu_copy_hint_20260615"] = "Copy Full is preserved inside the active calculation section. Open the active page and use its original Copy Full button."
    if c4.button("🔄 Reset UI State", key="main_menu_reset_ui_state_20260615", use_container_width=True):
        for key, value in {
            "active_page": "Home",
            "active_subpage": "",
            "tab_choice": "Home",
            "home_inner_tab": "Lunch",
            "lunch_active_subpage": "",
            "dinner_active_subpage": "",
            "research_active_subpage": "",
            "new7_main_menu_drawer_open": False,
            "menu_open": False,
        }.items():
            st.session_state[key] = value
        st.session_state["ui_navigation_click_ts"] = time.time()
        _safe_rerun()
    if st.session_state.get("main_menu_copy_hint_20260615"):
        st.info(st.session_state.get("main_menu_copy_hint_20260615"))


def _render_native_backup_controls() -> None:
    st.markdown("#### 🧱 Native Sidebar")
    st.caption(
        "Permanently disabled on desktop and phone. Use this Main Page Menu for all navigation and connection controls."
    )
    try:
        from ui.sidebar_hard_lock import disable_native_sidebar
        disable_native_sidebar("Native sidebar permanently disabled. Main Page Menu remains active.")
    except Exception:
        pass


def render_main_menu_drawer(current_tab: str | None = None) -> str:
    _soft_menu_css()
    pages = {"Home", "Lunch", "Dinner", "Morning", "Data Visualization", "Research", "AI Assistant", "Settings"}
    if current_tab and current_tab in pages:
        st.session_state.setdefault("active_page", current_tab)
    st.session_state.setdefault("active_page", st.session_state.get("tab_choice", "Home"))
    st.session_state.setdefault("active_subpage", "")

    with st.expander("☰ Open / Close — Main Page Menu", expanded=False):
        st.markdown(
            """
<div class="new7-card">
  <b>Stable Main-Page Menu</b><br>
  <span class="new7-menu-note">Ant Design navigation is the primary menu. The native Streamlit sidebar is permanently disabled on desktop and phone.</span>
</div>
            """,
            unsafe_allow_html=True,
        )
        try:
            from ui.antd_navigation_20260615 import safe_antd_navigation
            safe_antd_navigation("antd_main_navigation")
        except Exception as exc:
            st.warning("streamlit-antd-components not installed; using safe fallback navigation.")
            st.caption(f"Navigation fallback reason: {exc}")
            page_list = ["Home", "Lunch", "Dinner", "Morning", "Data Visualization", "Research", "AI Assistant", "Settings"]
            current = st.session_state.get("active_page", "Home")
            idx = page_list.index(current) if current in page_list else 0
            page = st.selectbox("Navigation", page_list, index=idx, key="hard_fallback_nav_20260615")
            st.session_state["active_page"] = page
            st.session_state["active_subpage"] = ""
            st.session_state["tab_choice"] = page
        _sync_status()
        _render_quick_actions()
        st.divider()
        try:
            from ui.sidebar_fallback_panel import render_sidebar_fallback_panel
            render_sidebar_fallback_panel(expanded=False)
        except Exception as exc:
            st.warning(f"Main-page sidebar replacement controls failed safely: {exc}")
        st.divider()
        _render_native_backup_controls()

    # Keep session_state as the single source of truth after the expander closes.
    return st.session_state.get("active_page", st.session_state.get("tab_choice", "Home"))
