"""Six principal Lunch fields with true load gates and bounded mobile projections.

The filename is retained because the active router and earlier releases reference
it. The renderer itself exposes the six preserved principal fields. Opening a
field only reads the last committed canonical generation; it never calls a
calculation builder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import json
import time

import pandas as pd
import streamlit as st


def _canonical() -> dict[str, Any]:
    for key in ("canonical_decision_result_20260617", "canonical_decision_result", "last_valid_canonical_decision_result_20260617"):
        value=st.session_state.get(key)
        if isinstance(value, Mapping): return dict(value)
    return {}


def _phone() -> bool:
    return bool(st.session_state.get("phone_mode", False) or st.session_state.get("logic_first_mobile_20260618", False))


def _frame(value: Any) -> pd.DataFrame:
    if isinstance(value,pd.DataFrame): return value
    if isinstance(value,Mapping):
        try: return pd.DataFrame([dict(value)])
        except Exception: return pd.DataFrame()
    if isinstance(value,(list,tuple)):
        try: return pd.DataFrame(list(value))
        except Exception: return pd.DataFrame()
    return pd.DataFrame()


def _bounded(df: pd.DataFrame, *, phone_rows: int=50, desktop_rows: int=200) -> pd.DataFrame:
    if df.empty: return df
    limit=phone_rows if _phone() else desktop_rows
    return df.head(limit).copy(deep=False)


def _identity(c: Mapping[str,Any]) -> dict[str,Any]:
    return {
        "calculation_id":str(c.get("canonical_calculation_id") or c.get("run_id") or ""),
        "calculation_generation":int(c.get("calculation_generation") or 0),
        "run_id":str(c.get("run_id") or c.get("canonical_calculation_id") or ""),
        "symbol":str(c.get("symbol") or "EURUSD"),"timeframe":str(c.get("timeframe") or "H1"),
        "source":str(c.get("source") or "UNKNOWN"),
        "latest_completed_h1":str(c.get("latest_completed_candle_time") or (c.get("market") or {}).get("latest_completed_candle_time") or ""),
        "record_time":str(c.get("latest_completed_candle_time") or (c.get("market") or {}).get("latest_completed_candle_time") or ""),
        "target_time":None,"horizon":None,"data_signature":str(c.get("data_signature") or ""),
        "logic_version":"lunch-render-budget-20260621-v1","settled_status":"NOT_APPLICABLE","is_revision":0,
    }


def _record_budget(c: Mapping[str,Any], field: str, started: float, *, rows: int=0, points: int=0, traces: int=0, payload_bytes: int=0) -> None:
    try:
        import psutil
        from core.history_quality_store_20260621 import append_mobile_render_budget
        ident=_identity(c)
        if not ident["calculation_id"] or not ident["latest_completed_h1"]: return
        row={**ident,"created_at":pd.Timestamp.now(tz="UTC").isoformat(),"viewport_profile":"IPHONE_11_PRO" if _phone() else "LAPTOP","field_name":field,"displayed_rows":int(rows),"chart_points":int(points),"chart_traces":int(traces),"payload_bytes":int(payload_bytes),"render_time_ms":(time.perf_counter()-started)*1000.0,"server_rss_bytes":int(psutil.Process().memory_info().rss),"budget_status":"PASS" if rows <= (50 if _phone() else 250) and points <= (400 if _phone() else 1500) else "OVER_BUDGET","failure_reason":None,"payload":{}}
        append_mobile_render_budget(row)
    except Exception:
        pass


def _quality_cards(c: Mapping[str,Any]) -> None:
    status=(c.get("data_quality") or {}).get("status") or (c.get("metadata") or {}).get("data_quality_status") or "INSUFFICIENT EVIDENCE"
    cols=st.columns(4)
    cols[0].metric("Quality",str(status))
    cols[1].metric("Generation",str(c.get("calculation_generation") or "—"))
    cols[2].metric("Latest H1",str(c.get("latest_completed_candle_time") or (c.get("market") or {}).get("latest_completed_candle_time") or "—")[:19])
    cols[3].metric("Source",str(c.get("source") or "—"))


def _full_metric_history(c: Mapping[str,Any]) -> pd.DataFrame:
    df=_frame(c.get("full_metric_history"))
    if df.empty:
        try:
            from core.history_evidence_store_20260620 import query_history
            df=query_history("full_metric_overall_history",columns=["latest_completed_h1","calculation_generation","metric_name","value_numeric","value_text","settled_status"],limit=500)
        except Exception: pass
    return df


def _decision_history(c: Mapping[str,Any]) -> pd.DataFrame:
    value=c.get("reverse_10_history")
    rows=[]
    if isinstance(value,Mapping):
        for decision,history in value.items():
            part=_frame(history)
            if not part.empty:
                part=part.copy(deep=False); part.insert(0,"Decision",str(decision)); rows.append(part)
    elif isinstance(value,(list,tuple,pd.DataFrame)):
        rows=[_frame(value)]
    if rows:
        try: return pd.concat(rows,ignore_index=True,sort=False)
        except Exception: pass
    try:
        from core.history_evidence_store_20260620 import query_history
        return query_history("protected_decision_history",columns=["latest_completed_h1","calculation_generation","condition","metric_name","value_numeric","value_text","settled_status"],limit=1000)
    except Exception: return pd.DataFrame()


def _download_exact(label: str, df: pd.DataFrame, filename: str, key: str) -> None:
    if df.empty: return
    if st.button(f"Prepare {label}",key=key+"_prepare",use_container_width=True): st.session_state[key]=True
    if st.session_state.get(key):
        st.download_button(label,df.to_csv(index=False).encode(),file_name=filename,mime="text/csv",key=key+"_download",use_container_width=True)


def _render_field1(c: Mapping[str,Any]) -> None:
    started=time.perf_counter(); _quality_cards(c)
    st.markdown("#### Overall Full Metric History — Last 25 Days")
    full=_full_metric_history(c); view=_bounded(full)
    if view.empty: st.info("INSUFFICIENT EVIDENCE — no valid rows are stored for this history.")
    else: st.dataframe(view,use_container_width=True,hide_index=True,height=420 if not _phone() else 330)
    _download_exact("Full Metric exact CSV",full,"overall_full_metric_history_25d.csv","field1_full_exact_20260621")
    st.markdown("#### All 10 Decision Histories — Last 25 Days")
    decisions=_decision_history(c); view2=_bounded(decisions)
    if view2.empty: st.info("INSUFFICIENT EVIDENCE — no valid rows are stored for the ten decision histories.")
    else: st.dataframe(view2,use_container_width=True,hide_index=True,height=420 if not _phone() else 330)
    _download_exact("All 10 decisions exact CSV",decisions,"all_10_decision_histories_25d.csv","field1_decisions_exact_20260621")
    payload=int(view.memory_usage(deep=True).sum() if not view.empty else 0)+int(view2.memory_usage(deep=True).sum() if not view2.empty else 0)
    _record_budget(c,"FIELD_1",started,rows=len(view)+len(view2),payload_bytes=payload)


def _render_field2(c: Mapping[str,Any]) -> None:
    started=time.perf_counter(); rendered=False
    try:
        from ui.powerbi_cached_renderer_20260619 import render_powerbi_cached
        render_powerbi_cached(); rendered=True
    except Exception: pass
    if not rendered:
        try:
            import tabs.dinner_morning_data_patch_20260614 as dinner
            dinner._render_lunch_red_prediction_line(); rendered=True
        except Exception: pass
    power=c.get("powerbi") or c.get("probabilistic_projection") or c.get("forecasts") or {}
    if isinstance(power,Mapping):
        compact={k:v for k,v in power.items() if not hasattr(v,"columns") and k not in {"historical_paths","full_history"}}
        st.json(compact,expanded=False)
    if not rendered and not power: st.info("INSUFFICIENT EVIDENCE — run Settings calculation once to publish the cached projection.")
    _record_budget(c,"FIELD_2",started,payload_bytes=len(json.dumps(power,default=str).encode()) if power else 0)


def _render_field3(c: Mapping[str,Any]) -> None:
    started=time.perf_counter(); regime=c.get("regime") or c.get("multiscale_regime") or {}
    if isinstance(regime,Mapping) and regime:
        cards=st.columns(4); cards[0].metric("Regime",str(regime.get("major_regime") or regime.get("current") or "—")); cards[1].metric("Alpha",str(regime.get("alpha") or "—")); cards[2].metric("Delta",str(regime.get("delta") or "—")); cards[3].metric("Reliability",str((c.get("reliability") or {}).get("score") or "—"))
        st.json(regime,expanded=False)
    else: st.info("INSUFFICIENT EVIDENCE — no committed regime generation.")
    _record_budget(c,"FIELD_3",started,payload_bytes=len(json.dumps(regime,default=str).encode()) if regime else 0)


def _render_field4(c: Mapping[str,Any]) -> None:
    started=time.perf_counter()
    try:
        import tabs.dinner_morning_data_patch_20260614 as dinner
        ns=__import__('tabs.home',fromlist=['*']).__dict__
        dinner._render_dinner(ns,ns.get("_render_lunch_data_visualization_inner_tab"))
    except Exception as exc:
        compact={"priority":c.get("priority"),"reliability":c.get("reliability"),"final_decision":c.get("final_decision"),"similar_day":c.get("similar_day_intelligence")}
        st.json(compact,expanded=False); st.caption(f"Combined legacy renderer fallback: {exc}")
    _record_budget(c,"FIELD_4",started)


def _render_field5(c: Mapping[str,Any]) -> None:
    started=time.perf_counter()
    try:
        from tabs.ai_assistant_lite import render_ai_assistant_lite_tab
        # Grounding is reconstructed from the committed canonical object, never by
        # rerunning Settings calculation.
        st.session_state.setdefault("canonical_decision_result",c)
        render_ai_assistant_lite_tab()
    except Exception as exc: st.warning(f"AI Assistant unavailable: {exc}")
    _record_budget(c,"FIELD_5",started)


def _render_field6(c: Mapping[str,Any]) -> None:
    started=time.perf_counter()
    try:
        from core.history_quality_store_20260621 import SCHEMAS
        from services.canonical_snapshot_store import DB_PATH
        import sqlite3
        table=st.selectbox("Research / quality history",list(SCHEMAS),key="quality_history_table_20260621")
        limit=50 if _phone() else 150
        conn=sqlite3.connect(str(DB_PATH),timeout=10,check_same_thread=False)
        try:
            columns=[str(r[1]) for r in conn.execute(f'PRAGMA table_info("{table}")')]
            projection=[x for x in ("latest_completed_h1","calculation_generation","record_time","settled_status","created_at") if x in columns]
            for candidate in ("issue_type","rule_id","column_name","processing_stage","viewport_profile","field_name","status","promotion_decision"):
                if candidate in columns: projection.append(candidate)
            projection=list(dict.fromkeys(projection))
            df=pd.read_sql_query(f'SELECT {",".join(chr(34)+x+chr(34) for x in projection)} FROM "{table}" ORDER BY created_at DESC LIMIT ?',conn,params=[limit]) if projection else pd.DataFrame()
            total=int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        finally: conn.close()
        st.caption(f"Grain and business key are documented in HISTORY_TABLE_CATALOG.csv · Stored rows: {total}")
        if df.empty: st.info("INSUFFICIENT EVIDENCE — the schema exists but no valid canonical rows have populated it yet.")
        else: st.dataframe(df,use_container_width=True,hide_index=True,height=360)
        _record_budget(c,"FIELD_6",started,rows=len(df),payload_bytes=int(df.memory_usage(deep=True).sum()) if not df.empty else 0)
    except Exception as exc: st.warning(f"Quality history browser unavailable: {exc}")


def render_lunch_six_core_fields(runtime_context: Mapping[str,Any] | None=None) -> None:
    c=_canonical()
    st.markdown("### 🍱 Lunch — Canonical EURUSD H1 Evidence")
    if not c:
        st.info("Run Calculation in Settings once. Lunch reads only the last valid completed canonical generation.")
    fields=(
        ("1. Open / Close — Full Metric 25-Day History + Decision Tables",_render_field1),
        ("2. Open / Close — Power BI Price Prediction Path",_render_field2),
        ("3. Open / Close — 25-Day Regime History + Lower / Medium / Higher Standards",_render_field3),
        ("4. Open / Close — Dinner Full Combined Intelligence",_render_field4),
        ("5. Open / Close — Grounded AI Assistant",_render_field5),
        ("6. Open / Close — Future Strategy Research History",_render_field6),
    )
    for idx,(label,renderer) in enumerate(fields,1):
        enabled=st.toggle(label,value=False,key=f"lunch_true_load_gate_{idx}_20260621")
        if enabled: renderer(c)


def render_lunch_four_core_fields(runtime_context: Mapping[str,Any] | None=None) -> None:
    render_lunch_six_core_fields(runtime_context)


__all__=["render_lunch_six_core_fields","render_lunch_four_core_fields"]
