"""Compact master control bar and the sole Settings calculation gate."""
from __future__ import annotations
from typing import Any, Mapping
import streamlit as st

def run_home_calculation_gate(ns: Mapping[str, Any] | None = None):
    from core.settings_run_orchestrator_20260617 import run_settings_calculation
    return run_settings_calculation(dict(ns or {}))

def render_home_master_control_bar(active_page: str = "") -> None:
    st.session_state.setdefault("active_page", active_page or "Settings")
