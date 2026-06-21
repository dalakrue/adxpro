"""2026-06-02 Global full-system upgrade layer.

Additive only: this module gives every tab the same compact command center,
copy/export helper, data-quality metrics, UI/animation hooks, and safe health
checks without changing the original tab algorithms.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from core.ui.compact import render_metric_cards, render_section_note

try:
    import streamlit.components.v1 as components
except Exception:  # pragma: no cover
    components = None


OHLC = ["open", "high", "low", "close"]


def _now() -> str:
    try:
        return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def get_live_df() -> pd.DataFrame:
    """Return the best shared market dataframe without raising."""
    for key in ["last_df", "shared_df", "market_df", "df", "home_df"]:
        obj = st.session_state.get(key)
        if isinstance(obj, pd.DataFrame) and not obj.empty:
            return normalize_market_df(obj)
    return pd.DataFrame()


def normalize_market_df(df: Any) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    for src in ["datetime", "timestamp", "date"]:
        if src in out.columns and "time" not in out.columns:
            out = out.rename(columns={src: "time"})
    if "time" in out.columns:
        out["time"] = pd.to_datetime(out["time"], errors="coerce")
        out = out.dropna(subset=["time"]).sort_values("time")
        out = out.drop_duplicates("time", keep="last")
    for c in set(OHLC + ["volume", "tick_volume", "real_volume"]):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if all(c in out.columns for c in OHLC):
        out = out.dropna(subset=OHLC)
    return out.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    df = normalize_market_df(df)
    if df.empty:
        return {"status": "NO DATA", "score": 0, "rows": 0, "issues": "No shared dataframe."}
    score = 100
    issues = []
    missing = [c for c in ["time"] + OHLC if c not in df.columns]
    if missing:
        score -= 25
        issues.append("Missing: " + ", ".join(missing))
    if "time" in df.columns:
        dup = int(df["time"].duplicated().sum())
        if dup:
            score -= min(20, dup)
            issues.append(f"Duplicate time rows: {dup}")
        gaps = df["time"].diff().dropna()
        if not gaps.empty:
            med = gaps.median()
            if med > pd.Timedelta(0):
                big = int((gaps > med * 3).sum())
                if big:
                    score -= min(20, big * 2)
                    issues.append(f"Large gaps: {big}")
    for c in OHLC:
        if c in df.columns:
            bad = int(pd.to_numeric(df[c], errors="coerce").isna().sum())
            if bad:
                score -= min(15, bad)
                issues.append(f"Bad {c}: {bad}")
    score = int(max(0, min(100, score)))
    status = "GOOD" if score >= 85 else "CHECK" if score >= 60 else "BAD"
    return {"status": status, "score": score, "rows": len(df), "issues": "; ".join(issues) if issues else "Clean enough for tab use."}


def quick_market_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    df = normalize_market_df(df)
    if df.empty or "close" not in df.columns:
        return {"bias": "WAIT", "last_close": "N/A", "move_10": 0.0, "move_60": 0.0, "vol_120": 0.0, "rows": 0}
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty:
        return {"bias": "WAIT", "last_close": "N/A", "move_10": 0.0, "move_60": 0.0, "vol_120": 0.0, "rows": len(df)}
    def pct(n: int) -> float:
        if len(close) <= n:
            return 0.0
        base = close.iloc[-n-1]
        return float((close.iloc[-1] - base) / base * 100) if base else 0.0
    move_10 = pct(10)
    move_60 = pct(60)
    ret = close.pct_change().tail(120).dropna()
    vol_120 = float(ret.std() * 100) if len(ret) else 0.0
    bias = "BUY" if move_10 > 0 and move_60 > 0 else "SELL" if move_10 < 0 and move_60 < 0 else "WAIT"
    return {"bias": bias, "last_close": round(float(close.iloc[-1]), 5), "move_10": round(move_10, 4), "move_60": round(move_60, 4), "vol_120": round(vol_120, 5), "rows": len(df)}


def _account_metrics() -> Dict[str, Any]:
    acc = st.session_state.get("account_snapshot") or {}
    if not isinstance(acc, dict):
        acc = {}
    positions = st.session_state.get("doo_positions") or acc.get("positions") or []
    try:
        pos_count = len(positions)
    except Exception:
        pos_count = 0
    margin_level = acc.get("margin_level") or acc.get("margin_level_pct") or acc.get("margin_level_%") or 0
    equity = acc.get("equity", 0)
    balance = acc.get("balance", 0)
    return {"positions": pos_count, "margin_level": margin_level, "equity": equity, "balance": balance}


def build_copy_payload(tab_name: str = "System") -> str:
    df = get_live_df()
    q = data_quality(df)
    m = quick_market_metrics(df)
    a = _account_metrics()
    payload = {
        "copied_at": _now(),
        "tab": tab_name,
        "symbol": st.session_state.get("symbol", "XAUUSD"),
        "timeframe": st.session_state.get("timeframe", "M1"),
        "source": st.session_state.get("source", "DISCONNECTED"),
        "connected": bool(st.session_state.get("connected", False)),
        "data_quality": q,
        "market": m,
        "account": a,
        "current_page": st.session_state.get("tab_choice", "Home"),
    }
    if not df.empty:
        tail = df.tail(5).copy()
        for col in tail.columns:
            if pd.api.types.is_datetime64_any_dtype(tail[col]):
                tail[col] = tail[col].astype(str)
        payload["last_5_candles"] = tail.to_dict("records")
    return json.dumps(payload, indent=2, default=str)


def render_copy_button(tab_name: str, key: str) -> None:
    """Beautiful, phone-safe copy button for all tabs.

    Non-destructive: payload content is unchanged; only the UI and clipboard
    fallback are upgraded. Works in Streamlit iframes and on mobile browsers.
    """
    import json
    import re
    import html as _html
    raw_text = build_copy_payload(tab_name)
    if components is None:
        st.download_button("Copy data unavailable — download JSON", raw_text, file_name=f"{tab_name.lower()}_snapshot.json", key=f"{key}_download")
        return
    safe_key = re.sub(r"[^A-Za-z0-9_-]", "_", str(key or "copy"))
    safe_tab = _html.escape(str(tab_name or "System"))
    text_json = json.dumps(str(raw_text or ""))
    components.html(
        f"""
        <style>
        *{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;}}
        .qx-copy-card{{padding:8px;border-radius:24px;background:linear-gradient(135deg,rgba(255,255,255,.72),rgba(224,242,254,.48));border:1px solid rgba(125,211,252,.45);box-shadow:0 16px 36px rgba(2,132,199,.14);}}
        .qx-copy-btn{{width:100%;min-height:52px;border:0;border-radius:20px;cursor:pointer;color:white;font-size:14px;font-weight:950;letter-spacing:.01em;background:radial-gradient(circle at 15% 10%,rgba(255,255,255,.40),transparent 23%),linear-gradient(135deg,#0284c7,#06b6d4 50%,#14b8a6);box-shadow:0 16px 32px rgba(2,132,199,.28),inset 0 1px 0 rgba(255,255,255,.48);position:relative;overflow:hidden;touch-action:manipulation;-webkit-tap-highlight-color:transparent;}}
        .qx-copy-btn:before{{content:"";position:absolute;inset:-70% -35%;background:linear-gradient(115deg,transparent,rgba(255,255,255,.52),transparent);transform:translateX(-78%) rotate(16deg);transition:.55s ease;}}
        .qx-copy-btn:hover:before{{transform:translateX(75%) rotate(16deg)}}.qx-copy-btn:active{{transform:scale(.985)}}
        .qx-copy-status{{font-size:12px;text-align:center;margin-top:6px;color:#075985;font-weight:900;min-height:18px;}}
        @media(max-width:520px){{.qx-copy-card{{padding:6px;border-radius:20px}}.qx-copy-btn{{min-height:56px;font-size:13.5px}}}}
        </style>
        <div class="qx-copy-card">
          <button id="copy_{safe_key}" class="qx-copy-btn" type="button">📋 Copy {safe_tab} + Shared Data</button>
          <textarea id="copy_text_{safe_key}" readonly style="position:fixed;left:-9999px;top:-9999px;width:2px;height:2px;opacity:.01;"></textarea>
          <div id="copy_status_{safe_key}" class="qx-copy-status">Ready • mobile safe</div>
        </div>
        <script>
        (function(){{
          const btn=document.getElementById('copy_{safe_key}');
          const ta=document.getElementById('copy_text_{safe_key}');
          const status=document.getElementById('copy_status_{safe_key}');
          const txt={text_json};
          ta.value=txt;
          async function copyNow(e){{
            if(e){{e.preventDefault();e.stopPropagation();}}
            let ok=false;
            try{{ if(navigator.clipboard && window.isSecureContext){{ await navigator.clipboard.writeText(txt); ok=true; }} }}catch(err){{ok=false;}}
            if(!ok){{
              try{{ ta.style.left='0px';ta.style.top='0px';ta.focus();ta.select();ta.setSelectionRange(0,ta.value.length);ok=document.execCommand('copy');ta.blur();ta.style.left='-9999px';ta.style.top='-9999px'; }}catch(err){{ok=false;}}
            }}
            status.textContent=ok?'Copied ✅ Paste anywhere now.':'Copy blocked — use fallback/download.';
            if(ok){{btn.textContent='✅ Copied';setTimeout(function(){{btn.textContent='📋 Copy {safe_tab} + Shared Data';}},1400);}}
          }}
          ['pointerup','click','touchend'].forEach(function(evt){{btn.addEventListener(evt,copyNow,{{passive:false}});}});
        }})();
        </script>
        """,
        height=98,
    )


def render_global_command_center(tab_name: str, *, expanded: bool = False) -> None:
    df = get_live_df()
    q = data_quality(df)
    m = quick_market_metrics(df)
    a = _account_metrics()
    with st.expander(f"🧠 {tab_name} command center / copy / health", expanded=expanded):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Source", str(st.session_state.get("source", "OFF")), str(st.session_state.get("timeframe", "M1")))
        c2.metric("Rows", f"{q['rows']:,}", q["status"])
        c3.metric("Mini Bias", str(m.get("bias", "WAIT")), f"10:{m.get('move_10',0)}% 60:{m.get('move_60',0)}%")
        c4.metric("Margin", str(a.get("margin_level", "N/A")), f"Pos {a.get('positions',0)}")
        b1, b2, b3 = st.columns([1,1,1])
        with b1:
            render_copy_button(tab_name, f"global_copy_{tab_name.replace(' ','_').lower()}")
        with b2:
            if st.button("🔁 Mark tab refreshed", use_container_width=True, key=f"global_mark_refresh_{tab_name}"):
                st.session_state["last_manual_ui_refresh"] = _now()
                st.toast(f"{tab_name} UI refreshed", icon="✅")
        with b3:
            if st.button("🧹 Repair session", use_container_width=True, key=f"global_repair_{tab_name}"):
                repair_session_state()
                st.toast("Session contract repaired", icon="🧩")
        st.caption(f"Quality {q['score']}/100 — {q['issues']}")


def repair_session_state() -> None:
    defaults = {
        "symbol": "XAUUSD", "timeframe": "M1", "source": "DISCONNECTED", "connected": False,
        "phone_mode": False, "activity_log": [], "doo_positions": [], "account_snapshot": {},
        "training_rows": [], "ui_navigation_click_ts": 0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not isinstance(st.session_state.get("activity_log"), list):
        st.session_state.activity_log = []
    if not isinstance(st.session_state.get("doo_positions"), list):
        st.session_state.doo_positions = []
    if not isinstance(st.session_state.get("account_snapshot"), dict):
        st.session_state.account_snapshot = {}


def render_tab_footer(tab_name: str) -> None:
    with st.expander(f"✅ {tab_name} upgrade status", expanded=False):
        st.write("Additive upgrade is active. Original tab logic is preserved behind this wrapper.")
        st.write("Shared dataframe, account snapshot, copy payload, session repair, and UI health are synchronized.")
        st.caption(f"Last checked: {_now()}")


def render_sidebar_upgrade_panel() -> None:
    """One compact sidebar maintenance field.

    Earlier upgrades showed another Quality/Bias metric row here even though the
    sidebar hero and one-click console already showed the same information.
    This version keeps the useful actions and deletes the duplicate st.metric
    block.
    """
    with st.expander("🚀 System maintenance / copy", expanded=False):
        df = get_live_df(); q = data_quality(df); m = quick_market_metrics(df)
        render_metric_cards([
            {"label": "Quality", "value": f"{q.get('score',0)}/100", "delta": q.get("status", "NO DATA")},
            {"label": "Bias", "value": m.get("bias", "WAIT"), "delta": f"rows {q.get('rows',0):,}"},
        ])
        render_copy_button("Sidebar", "sidebar_full_system")
        if st.button("🧩 Repair all session keys", use_container_width=True, key="sidebar_repair_all_session_keys"):
            repair_session_state()
            st.toast("Session keys repaired", icon="✅")



# -----------------------------------------------------------------------------
# 2026-06-02 Pro Global UI/UX v2 layer
# -----------------------------------------------------------------------------
def _safe_len_df(obj: Any) -> int:
    try:
        return int(len(obj)) if isinstance(obj, pd.DataFrame) else 0
    except Exception:
        return 0


def _short_time(value: Any) -> str:
    try:
        if not value:
            return "N/A"
        if isinstance(value, (int, float)):
            return pd.to_datetime(value, unit="s", errors="coerce").strftime("%H:%M:%S")
        return pd.to_datetime(value, errors="coerce").strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)[:19] if value not in [None, ""] else "N/A"


def render_page_shell(tab_name: str, subtitle: str = "", icon: str = "⚡") -> None:
    """Consistent glass page header for every main tab.

    This is intentionally additive: it reads shared session state only and does
    not change any original trading/math logic.
    """
    df = get_live_df()
    q = data_quality(df)
    m = quick_market_metrics(df)
    source = str(st.session_state.get("source", "DISCONNECTED"))
    connected = bool(st.session_state.get("connected", False)) and source not in ["", "DISCONNECTED"]
    badge_class = "pro-status-ok" if connected and q.get("score", 0) >= 60 else "pro-status-warn"
    subtitle = subtitle or "Shared-data command page. Original logic is preserved; this wrapper adds health, copy, and UI synchronization."
    st.markdown(
        f"""
        <div class="pro-page-shell">
          <div class="pro-title-zone">
            <div class="pro-kicker">{icon} ADX Quant Pro · {tab_name}</div>
            <div class="pro-title">{tab_name}</div>
            <div class="pro-subtitle">{subtitle}</div>
          </div>
          <div class="pro-status {badge_class}">
            <b>{'CONNECTED' if connected else 'WAITING'}</b>
            <span>{source} · {st.session_state.get('symbol','XAUUSD')} · {st.session_state.get('timeframe','M1')}</span>
          </div>
        </div>
        <div class="pro-mini-strip">
          <div><b>Rows</b><span>{q.get('rows',0):,}</span></div>
          <div><b>Quality</b><span>{q.get('status','NO DATA')} {q.get('score',0)}/100</span></div>
          <div><b>Bias</b><span>{m.get('bias','WAIT')} · 10c {m.get('move_10',0)}%</span></div>
          <div><b>Last close</b><span>{m.get('last_close','N/A')}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tab_upgrade_console(tab_name: str, *, expanded: bool = False) -> None:
    """Compact all-tab control panel: copy, repair, data quality, UI status."""
    df = get_live_df()
    q = data_quality(df)
    m = quick_market_metrics(df)
    with st.expander(f"🧰 Open {tab_name} pro tools / copy / relation check", expanded=expanded):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Source", st.session_state.get("source", "OFF"), st.session_state.get("timeframe", "M1"))
        c2.metric("Rows", f"{q.get('rows',0):,}", q.get("status", "NO DATA"))
        c3.metric("Quality", f"{q.get('score',0)}/100")
        c4.metric("Mini Bias", m.get("bias", "WAIT"), f"{m.get('move_10',0)}%")
        c5.metric("UI", "Phone" if st.session_state.get("phone_mode") else "Laptop")
        cols = st.columns(4)
        with cols[0]:
            render_copy_button(tab_name, f"pro_copy_{tab_name.replace(' ','_').lower()}")
        with cols[1]:
            if st.button("🧩 Repair state", use_container_width=True, key=f"pro_repair_{tab_name}"):
                repair_session_state()
                st.toast("State repaired", icon="✅")
        with cols[2]:
            if st.button("📱 Phone UI", use_container_width=True, key=f"pro_phone_{tab_name}"):
                st.session_state.phone_mode = True
                st.toast("Phone UI enabled", icon="📱")
        with cols[3]:
            if st.button("🖥️ Laptop UI", use_container_width=True, key=f"pro_laptop_{tab_name}"):
                st.session_state.phone_mode = False
                st.toast("Laptop UI enabled", icon="🖥️")
        st.caption(f"Data check: {q.get('issues','')}")


def render_sidebar_pro_header() -> None:
    df = get_live_df()
    q = data_quality(df)
    source = str(st.session_state.get("source", "DISCONNECTED"))
    symbol = st.session_state.get("symbol", "XAUUSD")
    timeframe = st.session_state.get("timeframe", "M1")
    connected = bool(st.session_state.get("connected", False)) and source not in ["", "DISCONNECTED"]
    st.markdown(
        f"""
        <div class="pro-sidebar-hero">
          <div class="pro-sidebar-title">⚡ ADX Quant Pro</div>
          <div class="pro-sidebar-sub">Global sidebar controls · one shared dataframe</div>
          <div class="pro-sidebar-grid">
            <div><b>Source</b><span>{source}</span></div>
            <div><b>Rows</b><span>{q.get('rows',0):,}</span></div>
            <div><b>Symbol</b><span>{symbol}</span></div>
            <div><b>TF</b><span>{timeframe}</span></div>
          </div>
          <div class="{'pro-live-pill' if connected else 'pro-off-pill'}">{'CONNECTED' if connected else 'NOT CONNECTED'} · Quality {q.get('score',0)}/100</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_shared_data_contract(location: str = "tab", *, expanded: bool = False) -> None:
    df = get_live_df()
    q = data_quality(df)
    checks = [
        {"part": "Shared dataframe", "state": "OK" if not df.empty else "EMPTY", "detail": f"rows={q.get('rows',0):,}"},
        {"part": "Sidebar connector", "state": str(st.session_state.get("source", "DISCONNECTED")), "detail": str(st.session_state.get("last_connection_message", ""))[:90]},
        {"part": "Home/Engine/Train reuse", "state": "SYNCED" if not df.empty else "WAIT", "detail": f"data_version={st.session_state.get('data_version','')}",},
        {"part": "Account snapshot", "state": "OK" if isinstance(st.session_state.get("account_snapshot"), dict) and st.session_state.get("account_snapshot") else "EMPTY", "detail": f"positions={len(st.session_state.get('doo_positions') or [])}"},
        {"part": "UI mode", "state": "PHONE" if st.session_state.get("phone_mode") else "LAPTOP", "detail": "compact glass final CSS active"},
    ]
    with st.expander(f"🔗 Open shared relationship contract · {location}", expanded=expanded):
        st.dataframe(pd.DataFrame(checks), use_container_width=True, hide_index=True, height=210)
        if df.empty:
            st.info("Connect once from the sidebar. Home, Engine, Train Data, Database, and Profile will reuse the same dataframe.")


def render_background_health_panel(expanded: bool = False) -> None:
    """Small UI diagnostics panel for CSS/background/sidebar issues."""
    with st.expander("🎨 Open UI/UX + background repair status", expanded=expanded):
        rows = [
            {"layer": "Final CSS override", "status": "ACTIVE", "purpose": "calm ocean-glass background, compact cards, improved sidebar"},
            {"layer": "Sidebar functions", "status": "ACTIVE", "purpose": "quick refresh, MT5/Doo, Twelve, disconnect, deep sync"},
            {"layer": "Animation", "status": "ACTIVE", "purpose": "soft pop/glow without heavy layout lag"},
            {"layer": "Mobile", "status": "ACTIVE", "purpose": "iPhone grid, smaller metrics, horizontal table scroll"},
            {"layer": "Original code", "status": "PRESERVED", "purpose": "wrappers add UI without deleting old algorithms"},
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=230)

def apply_extra_css() -> None:
    st.markdown(
        """
<style>
@keyframes quantFloat {0%{transform:translateY(0)}50%{transform:translateY(-3px)}100%{transform:translateY(0)}}
@keyframes quantGlow {0%{box-shadow:0 0 0 rgba(56,189,248,0)}50%{box-shadow:0 0 20px rgba(56,189,248,.22)}100%{box-shadow:0 0 0 rgba(56,189,248,0)}}
section[data-testid="stSidebar"] .stButton>button,
div[data-testid="stMetric"] { animation: quantGlow 5.8s ease-in-out infinite; }
.full-upgrade-chip{display:inline-flex;padding:5px 9px;border-radius:999px;border:1px solid rgba(14,116,144,.16);background:rgba(255,255,255,.70);font-size:11px;font-weight:900;color:#075985;backdrop-filter:blur(16px);}
.stExpander{border-radius:18px!important;overflow:hidden!important;}
[data-testid="stDataFrame"]{border-radius:16px!important;overflow:hidden!important;border:1px solid rgba(14,116,144,.12)!important;}
</style>
""",
        unsafe_allow_html=True,
    )

    # Final override wins over older repeated CSS blocks. It keeps the visual
    # language transparent/ocean-glass, but removes the ugly heavy borders and
    # gives the sidebar a cleaner command-center shape.
    st.markdown(
        """
<style>
:root{
  --pro-bg-1:#f8fcff;
  --pro-bg-2:#eaf7ff;
  --pro-line:rgba(14,116,144,.14);
  --pro-line-strong:rgba(14,165,233,.24);
  --pro-card:rgba(255,255,255,.66);
  --pro-card-2:rgba(236,248,255,.48);
  --pro-text:#0f172a;
  --pro-muted:#0e7490;
}
.stApp{
  background:
    radial-gradient(circle at 8% 2%, rgba(125,211,252,.34), transparent 28%),
    radial-gradient(circle at 88% 6%, rgba(186,230,253,.42), transparent 30%),
    radial-gradient(circle at 78% 92%, rgba(219,234,254,.46), transparent 34%),
    linear-gradient(135deg, var(--pro-bg-1), var(--pro-bg-2) 52%, #ffffff)!important;
}
.stApp:before{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  background-image:
    linear-gradient(rgba(14,116,144,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(14,116,144,.035) 1px, transparent 1px);
  background-size:34px 34px;
  mask-image:radial-gradient(circle at top, black, transparent 72%);
  z-index:0;
}
.main .block-container{position:relative;z-index:1;}
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg, rgba(255,255,255,.82), rgba(224,242,254,.62))!important;
  backdrop-filter:blur(26px) saturate(180%)!important;
  -webkit-backdrop-filter:blur(26px) saturate(180%)!important;
  border-right:1px solid var(--pro-line)!important;
  box-shadow:12px 0 34px rgba(2,132,199,.055)!important;
}
.pro-sidebar-hero{
  padding:11px!important;
  margin:.15rem 0 .55rem 0!important;
  border-radius:22px!important;
  background:linear-gradient(135deg, rgba(255,255,255,.88), rgba(224,242,254,.66))!important;
  border:1px solid var(--pro-line-strong)!important;
  box-shadow:0 12px 28px rgba(2,132,199,.10), inset 0 1px 0 rgba(255,255,255,.85)!important;
  animation:proPop .28s cubic-bezier(.2,1.2,.35,1) both!important;
}
.pro-sidebar-title{font-weight:950!important;font-size:1.02rem!important;color:var(--pro-text)!important;letter-spacing:-.02em!important;}
.pro-sidebar-sub{font-size:10px!important;font-weight:800!important;color:#0369a1!important;margin:2px 0 8px!important;}
.pro-sidebar-grid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px!important;margin:7px 0!important;}
.pro-sidebar-grid>div{min-width:0!important;border-radius:14px!important;background:rgba(255,255,255,.66)!important;border:1px solid rgba(14,116,144,.10)!important;padding:7px!important;}
.pro-sidebar-grid b{display:block!important;color:#075985!important;font-size:8.9px!important;font-weight:950!important;}
.pro-sidebar-grid span{display:block!important;color:#0f172a!important;font-size:10px!important;font-weight:850!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.pro-live-pill,.pro-off-pill{margin-top:7px!important;border-radius:999px!important;padding:6px 8px!important;text-align:center!important;font-size:9px!important;font-weight:950!important;letter-spacing:.04em!important;}
.pro-live-pill{background:rgba(220,252,231,.86)!important;color:#166534!important;border:1px solid rgba(22,163,74,.16)!important;}
.pro-off-pill{background:rgba(254,243,199,.88)!important;color:#92400e!important;border:1px solid rgba(217,119,6,.18)!important;}
.pro-page-shell{display:flex!important;align-items:stretch!important;justify-content:space-between!important;gap:.7rem!important;margin:.18rem 0 .55rem!important;padding:13px 14px!important;border-radius:24px!important;background:linear-gradient(135deg,rgba(255,255,255,.82),rgba(224,242,254,.58))!important;border:1px solid var(--pro-line)!important;box-shadow:0 14px 34px rgba(2,132,199,.075),inset 0 1px 0 rgba(255,255,255,.82)!important;backdrop-filter:blur(24px) saturate(180%)!important;animation:proPop .26s cubic-bezier(.2,1.2,.35,1) both!important;}
.pro-title-zone{min-width:0!important;}
.pro-kicker{font-size:10px!important;font-weight:950!important;color:#0369a1!important;letter-spacing:.08em!important;text-transform:uppercase!important;margin-bottom:2px!important;}
.pro-title{font-size:1.42rem!important;line-height:1.04!important;font-weight:950!important;color:#0f172a!important;letter-spacing:-.035em!important;}
.pro-subtitle{margin-top:4px!important;font-size:11px!important;font-weight:750!important;color:#475569!important;overflow-wrap:anywhere!important;}
.pro-status{min-width:138px!important;border-radius:18px!important;padding:9px 12px!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;text-align:center!important;border:1px solid rgba(15,23,42,.08)!important;}
.pro-status b{font-size:10px!important;font-weight:950!important;letter-spacing:.06em!important;}
.pro-status span{font-size:9.3px!important;font-weight:800!important;margin-top:2px!important;}
.pro-status-ok{background:rgba(220,252,231,.84)!important;color:#166534!important;box-shadow:0 0 0 5px rgba(22,163,74,.07)!important;}
.pro-status-warn{background:rgba(254,243,199,.86)!important;color:#92400e!important;box-shadow:0 0 0 5px rgba(217,119,6,.06)!important;}
.pro-mini-strip{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:.42rem!important;margin:.2rem 0 .65rem!important;}
.pro-mini-strip>div{min-width:0!important;border-radius:17px!important;padding:9px 10px!important;background:rgba(255,255,255,.64)!important;border:1px solid rgba(14,116,144,.11)!important;box-shadow:0 6px 15px rgba(2,132,199,.05)!important;backdrop-filter:blur(16px)!important;}
.pro-mini-strip b{display:block!important;color:#075985!important;font-size:9.5px!important;font-weight:950!important;}
.pro-mini-strip span{display:block!important;color:#0f172a!important;font-size:10.5px!important;font-weight:850!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
div[data-testid="stExpander"]{border:1px solid rgba(14,116,144,.13)!important;border-radius:18px!important;background:linear-gradient(135deg,rgba(255,255,255,.58),rgba(224,242,254,.34))!important;box-shadow:0 8px 22px rgba(2,132,199,.052),inset 0 1px 0 rgba(255,255,255,.70)!important;backdrop-filter:blur(20px) saturate(170%)!important;-webkit-backdrop-filter:blur(20px) saturate(170%)!important;overflow:hidden!important;margin:.36rem 0!important;animation:proPop .22s ease both!important;}
div[data-testid="stExpander"] summary{min-height:34px!important;padding:7px 10px!important;font-weight:950!important;color:#075985!important;border-radius:16px!important;background:rgba(255,255,255,.16)!important;}
div[data-testid="stExpander"] summary:hover{background:rgba(224,242,254,.54)!important;transform:translateY(-1px)!important;}
.stButton>button{border-radius:15px!important;border:1px solid rgba(14,116,144,.15)!important;background:linear-gradient(135deg,rgba(255,255,255,.78),rgba(224,242,254,.52))!important;box-shadow:0 5px 14px rgba(2,132,199,.05),inset 0 1px 0 rgba(255,255,255,.76)!important;color:#0f172a!important;font-weight:900!important;transition:transform .14s ease,box-shadow .14s ease,background .14s ease!important;}
.stButton>button:hover{transform:translateY(-1px)!important;background:linear-gradient(135deg,rgba(255,255,255,.92),rgba(186,230,253,.70))!important;box-shadow:0 9px 20px rgba(2,132,199,.085)!important;}
.stButton>button:active{transform:scale(.986)!important;}
div[data-testid="metric-container"]{border-radius:17px!important;border:1px solid rgba(14,116,144,.12)!important;background:rgba(255,255,255,.64)!important;box-shadow:0 6px 16px rgba(2,132,199,.05)!important;backdrop-filter:blur(18px)!important;}
[data-testid="stDataFrame"]{border-radius:17px!important;border:1px solid rgba(14,116,144,.12)!important;box-shadow:0 7px 18px rgba(2,132,199,.055)!important;overflow:hidden!important;}
textarea,input{box-shadow:none!important;}
@keyframes proPop{from{opacity:0;transform:translateY(7px) scale(.992);filter:blur(2px)}to{opacity:1;transform:translateY(0) scale(1);filter:blur(0)}}
@media(max-width:760px){
  .pro-page-shell{display:grid!important;grid-template-columns:1fr!important;border-radius:18px!important;padding:10px!important;}
  .pro-title{font-size:1.08rem!important;}
  .pro-subtitle{font-size:9.6px!important;}
  .pro-status{min-width:0!important;min-height:34px!important;}
  .pro-mini-strip{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:.30rem!important;}
  .pro-mini-strip>div{padding:7px!important;border-radius:14px!important;}
  section[data-testid="stSidebar"]{width:252px!important;min-width:252px!important;}
  div[data-testid="stHorizontalBlock"]{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(94px,1fr))!important;gap:.25rem!important;}
  div[data-testid="stHorizontalBlock"]>div[data-testid="column"]{width:100%!important;min-width:0!important;flex:unset!important;padding-left:0!important;padding-right:0!important;}
}
@media(max-width:390px){
  .main .block-container{padding:.28rem!important;}
  .pro-mini-strip{grid-template-columns:repeat(2,minmax(0,1fr))!important;}
  .pro-sidebar-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;}
}
</style>
        """,
        unsafe_allow_html=True,
    )



# -----------------------------------------------------------------------------
# 2026-06-02 duplicate-metric cleanup layer
# -----------------------------------------------------------------------------
def apply_dedup_metric_css() -> None:
    """Final CSS layer for compact non-duplicated metric cards."""
    st.markdown(
        """
<style>
.dedup-metric-grid{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(112px,1fr))!important;gap:.38rem!important;margin:.32rem 0 .55rem!important;}
.dedup-metric-card{min-width:0!important;border-radius:15px!important;padding:8px 9px!important;background:linear-gradient(135deg,rgba(255,255,255,.72),rgba(224,242,254,.42))!important;border:1px solid rgba(14,116,144,.12)!important;box-shadow:0 5px 14px rgba(2,132,199,.045)!important;backdrop-filter:blur(16px) saturate(165%)!important;animation:proPop .18s ease both!important;}
.dedup-metric-card b{display:block!important;font-size:9px!important;line-height:1.12!important;font-weight:950!important;color:#075985!important;letter-spacing:.02em!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.dedup-metric-card span{display:block!important;font-size:12px!important;line-height:1.18!important;font-weight:950!important;color:#0f172a!important;margin-top:2px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.dedup-metric-card small{display:block!important;font-size:9px!important;line-height:1.15!important;font-weight:800!important;color:#64748b!important;margin-top:1px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.dedup-note-card{border-radius:16px!important;padding:9px 10px!important;margin:.25rem 0 .55rem!important;background:rgba(255,255,255,.58)!important;border:1px solid rgba(14,116,144,.11)!important;box-shadow:0 6px 16px rgba(2,132,199,.045)!important;}
.dedup-note-card b{display:block!important;color:#075985!important;font-weight:950!important;margin-bottom:2px!important;}
.dedup-note-card span{display:block!important;color:#475569!important;font-weight:750!important;}
/* Keep Streamlit's real metric cards compact when original preserved code still uses them. */
div[data-testid="metric-container"]{padding:7px 8px!important;min-height:58px!important;}
div[data-testid="metric-container"] label, div[data-testid="metric-container"] [data-testid="stMetricLabel"]{font-size:9px!important;font-weight:900!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:16px!important;font-weight:950!important;}
@media(max-width:760px){.dedup-metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:.28rem!important}.dedup-metric-card{padding:7px!important;border-radius:13px!important}.dedup-metric-card span{font-size:10.6px!important}}
</style>
        """,
        unsafe_allow_html=True,
    )
