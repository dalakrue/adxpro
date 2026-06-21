"""Defensive adapters for optional Streamlit UI packages."""
from __future__ import annotations

def optional_import(name: str):
    try: return __import__(name)
    except Exception: return None

def library_status() -> dict[str, bool]:
    return {name: optional_import(name) is not None for name in ("streamlit_antd_components", "streamlit_option_menu")}
