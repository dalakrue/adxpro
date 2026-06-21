from __future__ import annotations
import streamlit as st

def apply_liquid_glass_theme() -> None:
    st.markdown("""<style>.stButton>button{min-height:44px;border-radius:12px} [data-testid='stMetric']{border-radius:14px;padding:.55rem}</style>""", unsafe_allow_html=True)
