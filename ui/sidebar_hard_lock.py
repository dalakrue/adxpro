"""Permanent native-sidebar policy.

The main-page menu is the only navigation system. Legacy public functions are
kept as compatibility shims, but none can re-enable Streamlit's native sidebar.
"""
from __future__ import annotations

import time
import streamlit as st

from ui.sidebar_permanent_disable_20260621 import (
    apply_permanent_sidebar_disable,
    enforce_sidebar_disabled_state,
)

NATIVE_SIDEBAR_DISABLED_KEY = "new7_native_sidebar_disabled_20260614"
NATIVE_SIDEBAR_STATUS_KEY = "new7_native_sidebar_status_20260614"
MAIN_DRAWER_KEY = "new7_main_menu_drawer_open"
LEGACY_DRAWER_KEY = "menu_open"


def init_sidebar_policy() -> None:
    enforce_sidebar_disabled_state()
    st.session_state[NATIVE_SIDEBAR_STATUS_KEY] = (
        "Native Streamlit sidebar is permanently disabled. Main Page Menu is the only menu."
    )
    st.session_state.setdefault(MAIN_DRAWER_KEY, False)
    st.session_state.setdefault(LEGACY_DRAWER_KEY, False)


def native_sidebar_disabled() -> bool:
    init_sidebar_policy()
    return True


def disable_native_sidebar(reason: str = "Native sidebar permanently disabled.") -> None:
    init_sidebar_policy()
    st.session_state[NATIVE_SIDEBAR_STATUS_KEY] = str(reason or "Native sidebar permanently disabled.")


def enable_native_sidebar_backup() -> None:
    """Compatibility no-op: the native sidebar cannot be unlocked."""
    init_sidebar_policy()
    st.session_state[NATIVE_SIDEBAR_STATUS_KEY] = (
        "Native sidebar remains permanently disabled. Use the Main Page Menu."
    )


def open_main_drawer() -> None:
    st.session_state[MAIN_DRAWER_KEY] = True
    st.session_state[LEGACY_DRAWER_KEY] = True
    st.session_state["ui_navigation_click_ts"] = time.time()


def close_main_drawer() -> None:
    st.session_state[MAIN_DRAWER_KEY] = False
    st.session_state[LEGACY_DRAWER_KEY] = False
    st.session_state["ui_navigation_click_ts"] = time.time()


def inject_sidebar_policy_css() -> None:
    init_sidebar_policy()
    apply_permanent_sidebar_disable()


def render_sidebar_policy_status() -> None:
    init_sidebar_policy()
    inject_sidebar_policy_css()
    st.markdown(
        """
<div class="new7-card">
  <b>🧱 Native Sidebar Permanently OFF</b><br>
  <span style="color:#64748b;font-size:.78rem;line-height:1.30;">
    The Streamlit sidebar and its phone open button are disabled. Use the
    <b>Main Page Menu</b> for navigation and connection controls.
  </span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(st.session_state.get(NATIVE_SIDEBAR_STATUS_KEY, "Sidebar policy ready."))
