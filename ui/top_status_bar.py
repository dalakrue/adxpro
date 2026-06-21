"""Small top status bar for the future-proof app shell."""
from __future__ import annotations
import streamlit as st

def render_top_status_bar(active_tab: str | None = None) -> None:
    tab = active_tab or st.session_state.get("active_page", st.session_state.get("tab_choice", "Lunch"))
    symbol = st.session_state.get("symbol", "EURUSD")
    timeframe = st.session_state.get("timeframe", "H1")
    source = st.session_state.get("source", "DISCONNECTED")
    try:
        df = st.session_state.get("last_df")
        rows = len(df) if df is not None else 0
    except Exception:
        rows = 0
    st.markdown(f'''
<div class="new7-top-status">
  <div style="font-weight:950;color:#0f172a;font-size:.96rem;">⚡ Quant Control Center</div>
  <div class="new7-status-line">
    <span class="new7-pill">Page: {tab}</span>
    <span class="new7-pill">{symbol}</span>
    <span class="new7-pill">{timeframe}</span>
    <span class="new7-pill">{source}</span>
    <span class="new7-pill">Rows: {rows:,}</span>
  </div>
</div>
''', unsafe_allow_html=True)
