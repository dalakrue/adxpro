"""Permanent native Streamlit sidebar removal.

The application uses its main-page menu. This module disables Streamlit's
built-in multipage navigation and removes the native sidebar/collapsed control
on desktop and mobile. It intentionally contains no DOM-click JavaScript.
"""
from __future__ import annotations

import streamlit as st

PERMANENT_SIDEBAR_DISABLED_KEY = "native_sidebar_permanently_disabled_20260621"


def enforce_sidebar_disabled_state() -> None:
    """Make all legacy sidebar flags resolve to disabled."""
    st.session_state[PERMANENT_SIDEBAR_DISABLED_KEY] = True
    st.session_state["new7_native_sidebar_disabled_20260614"] = True
    st.session_state["use_native_sidebar_fallback_20260619"] = False
    st.session_state["sidebar_force_hidden_20260614"] = True
    st.session_state["sidebar_close_requested_20260614"] = True
    st.session_state["sidebar_close_requested_native_only"] = True


def disable_streamlit_sidebar_navigation() -> None:
    """Disable Streamlit's automatic pages navigation when supported."""
    try:
        st.set_option("client.showSidebarNavigation", False)
    except Exception:
        # Project .streamlit/config.toml contains the same setting.
        pass


def inject_permanent_sidebar_css() -> None:
    """Hide every known native-sidebar element and reclaim full viewport width."""
    st.markdown(
        """
<style id="new7-permanent-no-native-sidebar-20260621">
/* Native Streamlit sidebar and every known open/collapsed control. */
section[data-testid="stSidebar"],
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarContent"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapsedControl"],
div[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarOverlay"] {
  display:none !important;
  visibility:hidden !important;
  opacity:0 !important;
  pointer-events:none !important;
  width:0 !important;
  min-width:0 !important;
  max-width:0 !important;
  height:0 !important;
  min-height:0 !important;
  overflow:hidden !important;
  transform:translateX(-200vw) !important;
  flex:0 0 0 !important;
}

/* Prevent an invisible sidebar or overlay from reserving phone width. */
html, body, .stApp, [data-testid="stAppViewContainer"] {
  width:100% !important;
  max-width:100% !important;
  overflow-x:hidden !important;
}
[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewContainer"] .main,
section.main {
  margin-left:0 !important;
  left:0 !important;
  width:100% !important;
  max-width:100% !important;
  flex:1 1 100% !important;
}

@media (max-width: 900px) {
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"],
  [data-testid="stSidebarOverlay"] {
    display:none !important;
    width:0 !important;
    min-width:0 !important;
    max-width:0 !important;
    transform:translateX(-200vw) !important;
  }
  .main .block-container,
  [data-testid="stAppViewContainer"] .main .block-container {
    width:100% !important;
    max-width:100vw !important;
    margin-left:0 !important;
    margin-right:0 !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def apply_permanent_sidebar_disable() -> None:
    disable_streamlit_sidebar_navigation()
    enforce_sidebar_disabled_state()
    inject_permanent_sidebar_css()
