"""Authoritative page/subpage state normalization (updated 2026-06-17).

``active_page`` and ``active_subpage`` are the only navigation inputs after
initialization. Older keys are maintained strictly as one-way mirrors.
"""
from __future__ import annotations

from typing import Dict, List

PAGES: List[str] = ["Settings", "Lunch", "Morning", "Research", "Other"]
SUBPAGES: Dict[str, List[str]] = {
    "Lunch": ["", "Full Metric Details + History", "PowerBI Projection", "Priority + Decision + Reliability", "Finder"],
    "Dinner": ["", "Regime Summary", "Combine Logic", "Combined Logic", "Unified Regime + Logic", "AI Assistant"],
    "Research": ["", "AI Assistant", "Research AI Assistant", "KNN / Greedy", "Quant Structure"],
}
ALIASES = {
    "Home": "Lunch", "Data Visualization": "Lunch", "AI Assistant": "Research", "Doo Prime": "Morning",
    "Regime": "Lunch", "Data Analysis": "Research", "Power BI": "Lunch", "PowerBI": "Lunch", "Metric": "Lunch",
}
SUBPAGE_PARENT = {sp: page for page, items in SUBPAGES.items() for sp in items if sp and sp != "AI Assistant"}


def _clean_text(value, default="") -> str:
    text = str(value or "").strip()
    return text if text else default


def stabilize_tab_state() -> None:
    try:
        import streamlit as st
    except Exception:
        return
    ss = st.session_state

    # Legacy values may seed a session once; after that they can never override
    # active_page/active_subpage.
    if "active_page" not in ss:
        ss["active_page"] = ss.get("tab_choice", "Settings")
    if "active_subpage" not in ss:
        page_seed = ALIASES.get(_clean_text(ss.get("active_page"), "Settings"), _clean_text(ss.get("active_page"), "Settings"))
        legacy_key = f"{page_seed.lower().replace(' ', '_')}_active_subpage"
        ss["active_subpage"] = ss.get(legacy_key, "")

    raw_page = _clean_text(ss.get("active_page"), "Settings")
    page = ALIASES.get(raw_page, raw_page)
    subpage = _clean_text(ss.get("active_subpage"), "")
    # Dinner is a hidden compatibility route. Old links land in Lunch Field 5
    # or Field 6 without exposing a second top-level menu choice.
    if raw_page == "Dinner":
        ss["lunch_focus_field_20260619"] = 6 if subpage == "AI Assistant" else 5
        page, subpage = "Lunch", ""
    if page not in PAGES:
        page = "Settings"
    if subpage in SUBPAGE_PARENT:
        page = SUBPAGE_PARENT[subpage]
    if subpage == "AI Assistant" and page not in {"Dinner", "Research"}:
        page = "Research"
    if subpage not in SUBPAGES.get(page, [""]):
        subpage = ""

    ss["active_page"] = page
    ss["active_subpage"] = subpage
    # One-way compatibility mirrors.
    ss["tab_choice"] = page
    if page in {"Lunch", "Dinner", "Morning", "Research"}:
        ss["home_inner_tab"] = page
    if page == "Lunch":
        ss["lunch_active_subpage"] = subpage
    elif page == "Dinner":
        ss["dinner_active_subpage"] = subpage
    elif page == "Research":
        ss["research_active_subpage"] = subpage
    ss["tab_state_stable_20260615"] = True
