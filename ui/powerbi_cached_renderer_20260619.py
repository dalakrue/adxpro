"""Display-only cached Power BI renderer; never imports a calculation builder."""
from __future__ import annotations
from typing import Any, Mapping
import pandas as pd
import streamlit as st

def render_powerbi_cached() -> None:
    canonical=st.session_state.get("canonical_decision_result_20260617") or st.session_state.get("canonical_decision_result") or {}
    power=canonical.get("powerbi") if isinstance(canonical,Mapping) else {}
    if not power and isinstance(canonical,Mapping): power=canonical.get("probabilistic_projection") or canonical.get("forecasts") or {}
    if not power:
        st.info("INSUFFICIENT EVIDENCE — no committed Power BI projection."); return
    if isinstance(power,Mapping):
        path=power.get("path") or power.get("forecast_path") or power.get("horizons")
        if isinstance(path,Mapping):
            rows=[]
            for h,v in path.items():
                if isinstance(v,Mapping): rows.append({"Horizon":h,**dict(v)})
                else: rows.append({"Horizon":h,"Forecast":v})
            if rows: st.dataframe(pd.DataFrame(rows).head(50),use_container_width=True,hide_index=True)
        st.json({k:v for k,v in power.items() if k not in {"historical_paths","full_history"} and not hasattr(v,"columns")},expanded=False)

def render(*args,**kwargs): return render_powerbi_cached()
