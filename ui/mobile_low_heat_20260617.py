from __future__ import annotations
import streamlit as st

def apply_mobile_low_heat_css(streamlit_module=st, phone_mode: bool=False) -> None:
    streamlit_module.markdown("""<style>
    @media(max-width:430px){.block-container{padding-left:.55rem!important;padding-right:.55rem!important;max-width:100%!important}div[data-testid='stHorizontalBlock']{flex-wrap:wrap!important}div[data-testid='stDataFrame']{max-width:100%;overflow-x:auto}button{min-height:44px!important}.js-plotly-plot{max-width:100%!important}}
    html,body,[data-testid='stAppViewContainer']{overflow-x:hidden!important}
    </style>""", unsafe_allow_html=True)

def should_enable_full_autorefresh(state, active_page: str, active_subpage: str="") -> bool:
    return bool(not state.get("phone_mode", False) and state.get("ws_enabled", False) and active_page in {"Home","Lunch","Data Visualization"})
