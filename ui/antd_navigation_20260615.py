"""Stable Ant Design navigation with safe Streamlit fallback (2026-06-15).

Display/state layer only. It never changes trading formulas, ML calculations,
regime calculations, PowerBI projections, tables, exports, or copy builders.
"""
from __future__ import annotations

import time
from typing import Dict, List, Tuple

import streamlit as st

try:  # requested safe import
    import streamlit_antd_components as sac  # type: ignore
    SAC_AVAILABLE = True
except Exception:  # pragma: no cover - package is optional at runtime
    sac = None  # type: ignore
    SAC_AVAILABLE = False

PAGES: List[str] = [
    "Home",
    "Lunch",
    "Dinner",
    "Morning",
    "Data Visualization",
    "Research",
    "AI Assistant",
    "Settings",
]

LUNCH_CHILDREN = [
    "Full Metric Details + History",
    "PowerBI Projection",
    "Priority + Decision + Reliability",
    "AI Assistant",
]
DINNER_CHILDREN = ["Regime Summary", "Combine Logic", "AI Assistant"]
RESEARCH_CHILDREN = ["Data Mining", "NLP", "KNN / Greedy", "Quant Structure"]

SUBPAGE_PARENT: Dict[str, str] = {
    "Full Metric Details + History": "Lunch",
    "PowerBI Projection": "Lunch",
    "Priority + Decision + Reliability": "Lunch",
    "Regime Summary": "Dinner",
    "Combine Logic": "Dinner",
    "Data Mining": "Research",
    "NLP": "Research",
    "KNN / Greedy": "Research",
    "Quant Structure": "Research",
}


def _init_nav_state() -> None:
    st.session_state.setdefault("active_page", "Home")
    st.session_state.setdefault("active_subpage", "")
    if st.session_state.get("active_page") not in PAGES:
        old = str(st.session_state.get("tab_choice", "") or "")
        st.session_state["active_page"] = old if old in PAGES else "Home"
    st.session_state.setdefault("tab_choice", st.session_state.get("active_page", "Home"))
    st.session_state.setdefault("home_inner_tab", "Lunch")


def _sync_legacy_state(page: str, subpage: str = "") -> Tuple[str, str]:
    """Sync AntD page/subpage to legacy state used by old renderers."""
    _init_nav_state()
    page = str(page or "Home").strip()
    subpage = str(subpage or "").strip()
    if page not in PAGES:
        page = "Home"
    if subpage in SUBPAGE_PARENT:
        page = SUBPAGE_PARENT[subpage]
    # Duplicate child label safety: nested AI Assistant is valid only when a
    # parent was already inferred as Lunch or Dinner. Otherwise use top page.
    if subpage == "AI Assistant" and page not in {"Lunch", "Dinner"}:
        page = "AI Assistant"
        subpage = ""

    st.session_state["active_page"] = page
    st.session_state["active_subpage"] = subpage
    st.session_state["tab_choice"] = page
    st.session_state["ui_navigation_click_ts"] = time.time()
    st.session_state["fast_tab_switch_active"] = True

    # Existing Home/Lunch renderers use home_inner_tab. Keep it aligned without
    # changing any calculation data.
    if page in {"Home", "Lunch"}:
        st.session_state["home_inner_tab"] = "Lunch"
    elif page == "Dinner":
        st.session_state["home_inner_tab"] = "Dinner"
    elif page == "Morning":
        st.session_state["home_inner_tab"] = "Morning"
    elif page == "Research":
        st.session_state["home_inner_tab"] = "Research"
    elif page == "Data Visualization":
        st.session_state["home_inner_tab"] = "Lunch"
    elif page == "AI Assistant":
        st.session_state["home_inner_tab"] = "Dinner"
        st.session_state["dinner_default_inner_tab"] = "AI Assistant"

    if page == "Lunch":
        st.session_state["lunch_active_subpage"] = subpage
    if page == "Dinner":
        st.session_state["dinner_active_subpage"] = subpage
    if page == "Research":
        st.session_state["research_active_subpage"] = subpage
        if subpage in {"Data Mining", "NLP"}:
            st.session_state["research_inner_tab"] = subpage
        elif subpage == "KNN / Greedy":
            st.session_state["research_inner_tab"] = "Data Mining"
        elif subpage == "Quant Structure":
            st.session_state["research_inner_tab"] = "Data Analysis"
    return page, subpage


def sync_active_page_to_legacy_state() -> Tuple[str, str]:
    """Public helper used by the page router."""
    return _sync_legacy_state(
        st.session_state.get("active_page", "Home"),
        st.session_state.get("active_subpage", ""),
    )


def _nested_options_for_page(page: str) -> List[str]:
    if page == "Lunch":
        return [""] + LUNCH_CHILDREN
    if page == "Dinner":
        return [""] + DINNER_CHILDREN
    if page == "Research":
        return [""] + RESEARCH_CHILDREN
    return [""]


def _render_synced_nested_selector(location_key: str) -> Tuple[str, str]:
    """Extra safe nested sync for mobile and duplicate child labels."""
    page = st.session_state.get("active_page", "Home")
    options = _nested_options_for_page(page)
    if len(options) <= 1:
        return _sync_legacy_state(page, "")
    current_sub = st.session_state.get("active_subpage", "")
    if current_sub not in options:
        current_sub = ""
    labels = ["Main"] + [x for x in options if x]
    current_label = current_sub or "Main"
    state_key = f"{location_key}_nested_choice_state"
    st.session_state[state_key] = current_label
    try:
        from ui.safe_tab_switch_20260615 import safe_tab_choice
        selected_label = safe_tab_choice(
            label="Nested navigation",
            options=labels,
            state_key=state_key,
            widget_key=f"{location_key}_safe_nested_navigation",
            default=current_label,
            horizontal=not bool(st.session_state.get("phone_mode", False)),
            rerun_on_change=False,
        )
    except Exception:
        selected_label = st.selectbox(
            "Nested navigation",
            labels,
            index=labels.index(current_label) if current_label in labels else 0,
            key=f"{location_key}_synced_nested_navigation",
            help="Syncs active_subpage with the Ant Design menu and works even when duplicate child labels exist.",
        )
    return _sync_legacy_state(page, "" if selected_label == "Main" else selected_label)


def _render_fallback(location_key: str) -> Tuple[str, str]:
    st.warning("streamlit-antd-components not installed; using safe fallback navigation.")
    current_page = st.session_state.get("active_page", "Home")
    if current_page not in PAGES:
        current_page = "Home"
    try:
        from ui.safe_tab_switch_20260615 import safe_tab_choice
        st.session_state[f"{location_key}_page_choice_state"] = current_page
        selected = safe_tab_choice(
            label="Navigation",
            options=PAGES,
            state_key=f"{location_key}_page_choice_state",
            widget_key=f"{location_key}_option_menu_main_navigation",
            default=current_page,
            icons=["house", "box-seam", "moon", "sun", "bar-chart", "search", "robot", "gear"],
            horizontal=not bool(st.session_state.get("phone_mode", False)),
            rerun_on_change=False,
        )
    except Exception:
        if bool(st.session_state.get("phone_mode", False)):
            selected = st.selectbox(
                "Navigation",
                PAGES,
                index=PAGES.index(current_page),
                key=f"{location_key}_fallback_main_navigation_select",
            )
        else:
            selected = st.radio(
                "Navigation",
                PAGES,
                index=PAGES.index(current_page),
                horizontal=True,
                key=f"{location_key}_fallback_main_navigation",
            )
    _sync_legacy_state(selected, "" if selected != st.session_state.get("active_page") else st.session_state.get("active_subpage", ""))
    return _render_synced_nested_selector(location_key + "_fallback")


def _menu_items():
    # Built from the requested Ant Design menu structure.
    return [
        sac.MenuItem("Home", icon="house"),
        sac.MenuItem("Lunch", icon="activity", children=[
            sac.MenuItem("Full Metric Details + History"),
            sac.MenuItem("PowerBI Projection"),
            sac.MenuItem("Priority + Decision + Reliability"),
            sac.MenuItem("AI Assistant"),
        ]),
        sac.MenuItem("Dinner", icon="moon", children=[
            sac.MenuItem("Regime Summary"),
            sac.MenuItem("Combine Logic"),
            sac.MenuItem("AI Assistant"),
        ]),
        sac.MenuItem("Morning", icon="sun"),
        sac.MenuItem("Data Visualization", icon="bar-chart"),
        sac.MenuItem("Research", icon="search", children=[
            sac.MenuItem("Data Mining"),
            sac.MenuItem("NLP"),
            sac.MenuItem("KNN / Greedy"),
            sac.MenuItem("Quant Structure"),
        ]),
        sac.MenuItem("AI Assistant", icon="robot"),
        sac.MenuItem("Settings", icon="gear"),
    ]


def safe_antd_navigation(location_key: str = "antd_main_navigation") -> Tuple[str, str]:
    """Render Ant Design navigation; fall back to Streamlit widgets if needed."""
    _init_nav_state()
    st.markdown(
        """
<style id="new7-antd-nav-mobile-20260615">
.new7-antd-nav-status{display:flex;flex-wrap:wrap;gap:6px;margin:.25rem 0 .45rem 0;}
.new7-antd-nav-pill{font-size:.73rem;font-weight:850;padding:4px 8px;border-radius:999px;background:rgba(239,246,255,.82);border:1px solid rgba(59,130,246,.14);color:#0f172a;}
@media(max-width:430px){
  div[data-testid="stRadio"] label{font-size:.72rem!important;}
  .new7-antd-nav-pill{font-size:.68rem;padding:3px 6px;}
  .new7-card{padding:9px 10px!important;border-radius:16px!important;}
}
</style>
        """,
        unsafe_allow_html=True,
    )

    if not SAC_AVAILABLE:
        return _render_fallback(location_key)

    try:
        selected = sac.menu(
            _menu_items(),
            open_all=True,
            key=location_key,
        )
    except Exception as exc:
        st.caption(f"Ant Design menu failed safely: {exc}")
        return _render_fallback(location_key + "_error")

    if selected:
        if selected == "AI Assistant":
            # The requested menu has one top-level AI Assistant plus nested AI
            # Assistant items under Lunch/Dinner. SAC returns labels, so infer
            # nested intent from the current parent and keep the separate top
            # page reachable from any other page.
            current_parent = st.session_state.get("active_page", "")
            if current_parent in {"Lunch", "Dinner"}:
                _sync_legacy_state(current_parent, "AI Assistant")
            else:
                _sync_legacy_state("AI Assistant", "")
        elif selected in PAGES:
            _sync_legacy_state(selected, "")
        elif selected in SUBPAGE_PARENT:
            _sync_legacy_state(SUBPAGE_PARENT[selected], selected)

    return _render_synced_nested_selector(location_key)


def render_active_nav_status() -> None:
    _init_nav_state()
    page = st.session_state.get("active_page", "Home")
    sub = st.session_state.get("active_subpage", "")
    sub_label = sub or "Main"
    st.markdown(
        f'<div class="new7-antd-nav-status"><span class="new7-antd-nav-pill">Active page: {page}</span><span class="new7-antd-nav-pill">Subpage: {sub_label}</span><span class="new7-antd-nav-pill">Native sidebar: backup only</span></div>',
        unsafe_allow_html=True,
    )
