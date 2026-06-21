"""Professional trading-terminal UI/UX layer.

Non-destructive visual upgrade only: it reads existing session/state values and
adds CSS/HTML widgets around the current app. It does not change trading logic,
connectors, orders, risk calculations, or reversal engines.
"""
from __future__ import annotations

import html
from typing import Any

import streamlit as st


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def _pick_market_state() -> tuple[str, str]:
    """Return CSS class + label from existing app state."""
    score = _num(st.session_state.get("last_reversal_score", st.session_state.get("reversal_score", 0)))
    adx = _num(st.session_state.get("adx", st.session_state.get("last_adx", 0)))

    # Try Doo deep market values without assuming exact key names.
    try:
        results = st.session_state.get("doo_deep_results", {}) or {}
        for item in results.values():
            market = item.get("market", {}) if isinstance(item, dict) else {}
            score = max(score, _num(market.get("reversal_score", market.get("10_reversal", 0))))
            adx = max(adx, _num(market.get("adx", market.get("ADX", 0))))
    except Exception:
        pass

    if score >= 7:
        return "danger", "REVERSAL DANGER"
    if adx > 25:
        return "trend", "TREND MODE"
    return "calm", "MARKET CALM"


def apply_pro_terminal_css() -> None:
    mode, label = _pick_market_state()
    st.session_state["pro_terminal_market_mode"] = mode
    st.markdown(
        f"""
<style>
:root {{
  --qx-bg-blue: rgba(56,189,248,.18);
  --qx-bg-green: rgba(34,197,94,.18);
  --qx-bg-red: rgba(248,113,113,.20);
  --qx-glass: rgba(255,255,255,.16);
  --qx-glass-strong: rgba(255,255,255,.28);
  --qx-line: rgba(255,255,255,.30);
  --qx-text: #0f172a;
  --qx-muted: #475569;
}}
.stApp::before {{
  content:"{html.escape(label)}";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:-2;
  background:
    radial-gradient(circle at 16% 12%, var(--qx-bg-blue), transparent 28%),
    radial-gradient(circle at 86% 18%, rgba(250,204,21,.12), transparent 30%),
    linear-gradient(115deg, rgba(248,250,252,.96), rgba(224,242,254,.82));
  animation: qxMarketBreath 7s ease-in-out infinite;
}}
.stApp::after {{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:-1;
  opacity:.55;
  background-image:
    linear-gradient(rgba(14,116,144,.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(14,116,144,.055) 1px, transparent 1px),
    radial-gradient(circle, rgba(14,165,233,.28) 1px, transparent 1.6px);
  background-size: 48px 48px, 48px 48px, 34px 34px;
  animation: qxGridFloat 18s linear infinite;
}}
body:has(.qx-market-danger) .stApp::before {{
  background:
    radial-gradient(circle at 12% 20%, var(--qx-bg-red), transparent 28%),
    radial-gradient(circle at 82% 16%, rgba(251,146,60,.25), transparent 30%),
    linear-gradient(115deg, rgba(255,247,237,.96), rgba(254,226,226,.72));
}}
body:has(.qx-market-trend) .stApp::before {{
  background:
    radial-gradient(circle at 14% 16%, var(--qx-bg-green), transparent 28%),
    radial-gradient(circle at 82% 20%, rgba(56,189,248,.20), transparent 30%),
    linear-gradient(115deg, rgba(240,253,244,.96), rgba(224,242,254,.76));
}}
section[data-testid="stSidebar"] {{
  background:linear-gradient(160deg, rgba(255,255,255,.30), rgba(224,242,254,.18))!important;
  backdrop-filter: blur(30px) saturate(190%)!important;
  -webkit-backdrop-filter: blur(30px) saturate(190%)!important;
  box-shadow: 14px 0 42px rgba(2,132,199,.10)!important;
  animation: qxSidebarIn .38s ease both;
}}
section[data-testid="stSidebar"] .stButton>button:hover {{
  box-shadow: 0 0 0 1px rgba(56,189,248,.28), 0 10px 24px rgba(2,132,199,.12)!important;
}}
/* V27: make Home tab and Sidebar buttons feel like the premium copy buttons */
.stButton>button, section[data-testid="stSidebar"] .stButton>button {{
  min-height:46px!important;
  border-radius:18px!important;
  border:1px solid rgba(125,211,252,.36)!important;
  background:radial-gradient(circle at 12% 10%,rgba(255,255,255,.46),transparent 22%),linear-gradient(135deg,rgba(2,132,199,.92),rgba(6,182,212,.88) 52%,rgba(20,184,166,.88))!important;
  color:white!important;
  font-weight:950!important;
  box-shadow:0 12px 26px rgba(2,132,199,.20), inset 0 1px 0 rgba(255,255,255,.42)!important;
  touch-action:manipulation!important;
  -webkit-tap-highlight-color:transparent!important;
  transition:transform .12s ease, box-shadow .12s ease, filter .12s ease!important;
}}
.stButton>button:hover, section[data-testid="stSidebar"] .stButton>button:hover {{
  filter:saturate(1.08)!important;
  transform:translateY(-1px)!important;
  box-shadow:0 16px 34px rgba(2,132,199,.25), inset 0 1px 0 rgba(255,255,255,.48)!important;
}}
.stButton>button:active, section[data-testid="stSidebar"] .stButton>button:active {{ transform:scale(.985)!important; }}
@media(max-width:520px){{
  .stButton>button, section[data-testid="stSidebar"] .stButton>button {{ min-height:52px!important; border-radius:20px!important; font-size:14px!important; }}
}}
div[data-testid="metric-container"] {{
  transform-style:preserve-3d!important;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease!important;
  animation: qxMetricRise .32s ease both;
}}
div[data-testid="metric-container"]:hover {{
  transform: translateY(-3px) perspective(700px) rotateX(1.4deg)!important;
  border-color: rgba(14,165,233,.30)!important;
  box-shadow: 0 16px 34px rgba(2,132,199,.13), inset 0 1px 0 rgba(255,255,255,.70)!important;
}}
.qx-market-calm,.qx-market-trend,.qx-market-danger {{ display:block; }}
.qx-terminal-hero {{
  position:relative; overflow:hidden; margin:.35rem 0 .75rem; padding:14px; border-radius:26px;
  background:linear-gradient(135deg, rgba(255,255,255,.34), rgba(224,242,254,.18));
  border:1px solid rgba(255,255,255,.36); backdrop-filter:blur(24px) saturate(190%);
  box-shadow:0 20px 48px rgba(2,132,199,.10), inset 0 1px 0 rgba(255,255,255,.72);
}}
.qx-terminal-hero::before {{ content:""; position:absolute; inset:-30%; background:conic-gradient(from 90deg, transparent, rgba(56,189,248,.22), transparent, rgba(34,197,94,.16), transparent); animation: qxSpin 10s linear infinite; }}
.qx-terminal-inner {{ position:relative; z-index:1; display:grid; grid-template-columns:1.25fr .75fr; gap:12px; align-items:center; }}
.qx-terminal-title {{ font-weight:950; letter-spacing:-.04em; font-size:1.42rem; color:#0f172a; }}
.qx-terminal-sub {{ color:#475569; font-weight:750; margin-top:4px; }}
.qx-terminal-badges {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }}
.qx-chip {{ border-radius:999px; padding:5px 9px; background:rgba(255,255,255,.38); border:1px solid rgba(14,116,144,.14); color:#075985; font-weight:900; }}
.qx-hero-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }}
.qx-hero-card {{ border-radius:20px; padding:11px; min-height:78px; background:rgba(255,255,255,.34); border:1px solid rgba(255,255,255,.30); box-shadow:0 10px 24px rgba(15,23,42,.06); transition:.18s ease; }}
.qx-hero-card:hover {{ transform:translateY(-4px) scale(1.01); box-shadow:0 18px 36px rgba(2,132,199,.13); }}
.qx-hero-card b {{ display:block; color:#075985; font-size:10px; letter-spacing:.05em; text-transform:uppercase; }}
.qx-hero-card span {{ display:block; color:#0f172a; font-size:1.28rem; font-weight:950; margin-top:6px; }}
.qx-pulse-wrap {{ display:flex; align-items:center; justify-content:center; margin:.35rem 0 .75rem; }}
.qx-pulse-ring {{ width:178px; height:178px; border-radius:50%; display:flex; align-items:center; justify-content:center; text-align:center; background:conic-gradient(from 0deg, #22c55e var(--score), rgba(148,163,184,.18) 0); box-shadow:0 0 0 10px rgba(255,255,255,.34), 0 18px 46px rgba(2,132,199,.12); animation:qxPulse 2.2s ease-in-out infinite; }}
.qx-pulse-core {{ width:128px; height:128px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(255,255,255,.72); border:1px solid rgba(14,116,144,.14); backdrop-filter:blur(18px); }}
.qx-pulse-core strong {{ font-size:2rem; font-weight:950; color:#0f172a; line-height:1; }}
.qx-pulse-core small {{ font-weight:950; color:#075985; margin-top:5px; }}
.qx-alert-popup {{ position:sticky; top:8px; z-index:99; margin:.35rem 0 .65rem; padding:12px 14px; border-radius:22px; background:linear-gradient(135deg, rgba(254,242,242,.96), rgba(255,247,237,.92)); border:1px solid rgba(239,68,68,.30); color:#7f1d1d; box-shadow:0 18px 42px rgba(239,68,68,.16); animation: qxSlideRight .38s ease both, qxDangerGlow 1.5s ease-in-out infinite; }}
.qx-alert-popup b {{ display:block; font-size:1rem; font-weight:950; }}
.qx-alert-popup span {{ display:block; font-weight:800; margin-top:4px; }}
.qx-heatmap {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:7px; margin:.35rem 0 .7rem; }}
.qx-heat {{ border-radius:18px; padding:9px; text-align:center; background:rgba(255,255,255,.42); border:1px solid rgba(14,116,144,.13); box-shadow:0 8px 20px rgba(2,132,199,.06); }}
.qx-heat b {{ display:block; color:#475569; font-size:9.5px; font-weight:950; }} .qx-heat span {{ display:block; font-size:1.25rem; margin-top:4px; }}
.qx-timeline {{ display:grid; gap:7px; margin:.3rem 0 .7rem; }}
.qx-line-row {{ display:grid; grid-template-columns:86px 1fr 48px; gap:8px; align-items:center; }}
.qx-line-date {{ color:#475569; font-weight:900; }} .qx-line-bar {{ height:13px; border-radius:999px; background:rgba(148,163,184,.18); overflow:hidden; }} .qx-line-fill {{ height:100%; border-radius:999px; background:linear-gradient(90deg,#38bdf8,#22c55e,#f59e0b,#ef4444); width:var(--w); }} .qx-line-score {{ font-weight:950; color:#0f172a; text-align:right; }}
.qx-assistant {{ position:fixed; right:18px; bottom:18px; z-index:1000; width:245px; max-width:calc(100vw - 36px); border-radius:24px; padding:12px; background:linear-gradient(135deg, rgba(255,255,255,.46), rgba(224,242,254,.28)); border:1px solid rgba(255,255,255,.40); backdrop-filter:blur(24px) saturate(190%); box-shadow:0 18px 44px rgba(2,132,199,.16); }}
.qx-assistant-title {{ font-weight:950; color:#075985; margin-bottom:6px; }} .qx-assistant-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; }} .qx-assistant-cell {{ border-radius:14px; padding:7px; background:rgba(255,255,255,.42); }} .qx-assistant-cell b {{ display:block; color:#64748b; font-size:8.5px; }} .qx-assistant-cell span {{ display:block; color:#0f172a; font-weight:950; margin-top:2px; }}
.qx-finder-shell {{ padding:12px; border-radius:24px; background:linear-gradient(135deg, rgba(255,255,255,.28), rgba(224,242,254,.18)); border:1px solid rgba(255,255,255,.32); backdrop-filter:blur(22px) saturate(185%); box-shadow:0 16px 40px rgba(2,132,199,.09); }}
@keyframes qxMarketBreath {{ 0%,100%{{filter:saturate(1)}} 50%{{filter:saturate(1.18)}} }}
@keyframes qxGridFloat {{ from{{background-position:0 0,0 0,0 0}} to{{background-position:48px 48px,48px 48px,34px 34px}} }}
@keyframes qxSidebarIn {{ from{{transform:translateX(-10px);opacity:.85}} to{{transform:translateX(0);opacity:1}} }}
@keyframes qxMetricRise {{ from{{opacity:.25; transform:translateY(6px)}} to{{opacity:1; transform:translateY(0)}} }}
@keyframes qxSpin {{ to{{transform:rotate(360deg)}} }}
@keyframes qxPulse {{ 0%,100%{{transform:scale(1)}} 50%{{transform:scale(1.025)}} }}
@keyframes qxSlideRight {{ from{{opacity:0; transform:translateX(26px)}} to{{opacity:1; transform:translateX(0)}} }}
@keyframes qxDangerGlow {{ 0%,100%{{box-shadow:0 18px 42px rgba(239,68,68,.12)}} 50%{{box-shadow:0 18px 58px rgba(239,68,68,.30)}} }}
@media(max-width:760px) {{
 .qx-terminal-inner {{ grid-template-columns:1fr; }} .qx-hero-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .qx-heatmap {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .qx-assistant {{ position:relative; right:auto; bottom:auto; width:auto; margin:.5rem 0; }} .qx-pulse-ring {{ width:148px; height:148px; }} .qx-pulse-core {{ width:108px; height:108px; }}
}}
</style>
<div class="qx-market-{mode}"></div>
""",
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# 2026-06-03 Pro Terminal UI/UX v2.1 additive runtime layer
# -----------------------------------------------------------------------------
def _first_existing(keys: list[str], default: Any = None) -> Any:
    for key in keys:
        val = st.session_state.get(key)
        if val not in [None, "", [], {}]:
            return val
    return default


def _safe_pct(v: Any, default: float = 0.0) -> float:
    return _clamp(_num(v, default), 0, 100)


def _latest_quality_status() -> tuple[str, int, int]:
    try:
        import pandas as pd
        df = _first_existing(["last_df", "shared_df", "market_df", "df"], None)
        rows = int(len(df)) if isinstance(df, pd.DataFrame) else 0
        q = st.session_state.get("last_data_quality", {}) or {}
        score = int(_safe_pct(q.get("score", 100 if rows >= 100 else 0)))
        status = str(q.get("status", "GOOD" if score >= 85 else "CHECK" if score >= 60 else "NO DATA"))
        return status, score, rows
    except Exception:
        return "CHECK", 0, 0


def _terminal_snapshot() -> dict[str, Any]:
    mode, _label = _pick_market_state()
    status, quality, rows = _latest_quality_status()
    account = st.session_state.get("account_snapshot") or {}
    if not isinstance(account, dict):
        account = {}
    margin = _first_existing([
        "margin_level_pct", "doo_margin_level", "margin_level", "account_margin_level_pct"
    ], account.get("margin_level", account.get("margin_level_pct", 0)))
    reversal = _first_existing(["last_reversal_score", "reversal_score", "home_last_reversal_score"], 0)
    fat_tail = _first_existing(["fat_tail_z", "last_fat_tail_z", "doo_fat_tail_z"], 0)
    adx = _first_existing(["adx", "last_adx", "doo_adx"], 0)
    source = st.session_state.get("source", "DISCONNECTED")
    symbol = st.session_state.get("symbol", "XAUUSD")
    tf = st.session_state.get("timeframe", "M1")
    margin_float = _num(margin, 0)
    margin_safety = max(0, min(100, margin_float - 30)) if margin_float else 0
    pulse = int(max(0, min(100, quality * .40 + min(_num(adx), 45) * .75 + margin_safety * .25 - _num(reversal) * 3.2)))
    return {
        "mode": mode,
        "source": source,
        "symbol": symbol,
        "timeframe": tf,
        "rows": rows,
        "quality": quality,
        "status": status,
        "margin": margin_float,
        "margin_safety": int(margin_safety),
        "reversal": int(round(_num(reversal, 0))),
        "fat_tail": _num(fat_tail, 0),
        "adx": _num(adx, 0),
        "pulse": pulse,
    }


def apply_pro_terminal_runtime_helpers() -> None:
    """Final CSS/JS for mobile copy, table scroll, sticky headers, sidebar glow.

    This is intentionally UI-only. It does not touch indicators, reversal logic,
    data connectors, account state, or orders.
    """
    st.markdown(
        """
<style>
/* Smart Sidebar Pro */
section[data-testid="stSidebar"] details,
section[data-testid="stSidebar"] [data-testid="stExpander"]{
  border-radius:18px!important;
  border:1px solid rgba(14,116,144,.13)!important;
  background:rgba(255,255,255,.24)!important;
  box-shadow:0 8px 24px rgba(2,132,199,.055)!important;
  margin-bottom:8px!important;
}
section[data-testid="stSidebar"] summary{font-weight:950!important;color:#075985!important;}
section[data-testid="stSidebar"] .stButton>button{
  min-height:40px!important;
  border-radius:16px!important;
  font-weight:950!important;
  transition:transform .16s ease, box-shadow .16s ease, background .16s ease!important;
}
section[data-testid="stSidebar"] .stButton>button:hover{
  transform:translateY(-2px)!important;
  background:linear-gradient(135deg,rgba(255,255,255,.88),rgba(224,242,254,.62))!important;
}
/* st.metric replacement look */
div[data-testid="metric-container"]{
  border-radius:22px!important;
  padding:13px 14px!important;
  background:linear-gradient(135deg,rgba(255,255,255,.46),rgba(224,242,254,.22))!important;
  border:1px solid rgba(14,116,144,.14)!important;
  backdrop-filter:blur(20px) saturate(185%)!important;
  -webkit-backdrop-filter:blur(20px) saturate(185%)!important;
}
div[data-testid="metric-container"] label,
div[data-testid="metric-container"] [data-testid="stMetricLabel"]{font-size:.72rem!important;font-weight:950!important;color:#075985!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1.28rem!important;font-weight:950!important;color:#0f172a!important;}
/* All-table upgrade */
[data-testid="stDataFrame"], .stDataFrame, div[data-testid="stTable"]{
  width:100%!important; max-width:100%!important; overflow:auto!important;
  border-radius:18px!important; border:1px solid rgba(14,116,144,.13)!important;
  box-shadow:0 12px 28px rgba(2,132,199,.07)!important;
}
[data-testid="stDataFrame"] *{font-size:12px!important;}
[data-testid="stDataFrame"] div[role="columnheader"]{
  position:sticky!important; top:0!important; z-index:3!important;
  background:rgba(240,249,255,.96)!important; font-weight:950!important;
}
/* Home/sidebar/inner-tab glass terminal replacement layer */
.stApp{background:linear-gradient(115deg,#f8fbff 0%,#e8f8ff 44%,#eefcff 100%)!important;}
.block-container{max-width:1420px!important;padding-top:.8rem!important;}
[data-testid="stHeader"]{background:rgba(255,255,255,.18)!important;backdrop-filter:blur(14px)!important;}
.stTabs [data-baseweb="tab-list"]{gap:8px!important;overflow-x:auto!important;}
.stTabs [data-baseweb="tab"]{border-radius:999px!important;background:rgba(255,255,255,.40)!important;border:1px solid rgba(14,116,144,.13)!important;font-weight:950!important;min-height:42px!important;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(224,242,254,.92),rgba(255,255,255,.72))!important;box-shadow:0 12px 24px rgba(2,132,199,.10)!important;}
[data-testid="stExpander"]{border-radius:20px!important;border:1px solid rgba(14,116,144,.13)!important;background:rgba(255,255,255,.30)!important;box-shadow:0 10px 26px rgba(2,132,199,.055)!important;overflow:hidden!important;}
[data-testid="stExpander"] summary{font-weight:950!important;color:#075985!important;}
.stButton>button,.stDownloadButton>button{border-radius:999px!important;border:1px solid rgba(14,116,144,.17)!important;background:linear-gradient(135deg,rgba(255,255,255,.78),rgba(224,242,254,.46))!important;color:#075985!important;font-weight:950!important;box-shadow:0 8px 18px rgba(2,132,199,.07)!important;touch-action:manipulation!important;-webkit-tap-highlight-color:transparent!important;}
.stButton>button:active,.stDownloadButton>button:active{transform:scale(.985)!important;}
textarea,input,[data-baseweb="select"]>div{border-radius:16px!important;background:rgba(255,255,255,.58)!important;border-color:rgba(14,116,144,.16)!important;}
/* Mobile alignment */
@media(max-width:760px){
  .block-container{padding: .65rem .48rem 5.4rem!important;}
  div[data-testid="column"]{min-width:calc(50% - .45rem)!important; flex:1 1 calc(50% - .45rem)!important;}
  div[data-testid="stHorizontalBlock"]{gap:.42rem!important; flex-wrap:wrap!important; align-items:stretch!important;}
  div[data-testid="metric-container"]{min-height:82px!important;padding:9px!important;}
  div[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1.02rem!important;line-height:1.1!important;}
  .stButton>button,.stDownloadButton>button{min-height:46px!important;font-size:.82rem!important;padding:.45rem .55rem!important;white-space:normal!important;}
  section[data-testid="stSidebar"]{width:min(88vw,340px)!important;}
  [data-testid="stDataFrame"]{overflow-x:auto!important;}
  .qx-terminal-title{font-size:1.05rem!important;}
  .qx-terminal-sub{font-size:.82rem!important;}
  .qx-terminal-hero{padding:10px!important;border-radius:22px!important;}
  .qx-hero-card{min-height:68px!important;padding:9px!important;}
}
/* Mobile/browser copy button reliability visual */
.qx-copy-mobile-btn{
  width:100%;min-height:50px;border:1px solid rgba(14,116,144,.20);border-radius:18px;cursor:pointer;
  font-weight:950;letter-spacing:.01em;background:linear-gradient(135deg,rgba(14,165,233,.95),rgba(45,212,191,.88));color:#ffffff;
  box-shadow:0 14px 30px rgba(2,132,199,.20), inset 0 1px 0 rgba(255,255,255,.40);
  position:relative;overflow:hidden;transition:transform .14s ease,box-shadow .14s ease,filter .14s ease;
  touch-action:manipulation;-webkit-tap-highlight-color:transparent;
}
.qx-copy-mobile-btn:before{content:"";position:absolute;inset:-70% -35%;background:linear-gradient(120deg,transparent,rgba(255,255,255,.42),transparent);transform:translateX(-70%) rotate(18deg);transition:transform .55s ease;pointer-events:none;}
.qx-copy-mobile-btn:hover{transform:translateY(-1px);filter:saturate(1.08);box-shadow:0 18px 38px rgba(2,132,199,.26), inset 0 1px 0 rgba(255,255,255,.48);}
.qx-copy-mobile-btn:hover:before{transform:translateX(75%) rotate(18deg);}
.qx-copy-mobile-btn:active{transform:scale(.985);}
.qx-command-lite{margin:.25rem 0 .65rem;padding:12px;border-radius:24px;background:linear-gradient(135deg,rgba(255,255,255,.38),rgba(224,242,254,.22));border:1px solid rgba(255,255,255,.35);backdrop-filter:blur(22px) saturate(180%);box-shadow:0 16px 40px rgba(2,132,199,.08);animation:qxPopFloat .42s ease both;position:relative;overflow:hidden}.qx-command-lite:before{content:"";position:absolute;inset:-40%;background:radial-gradient(circle at 20% 30%,rgba(56,189,248,.16),transparent 28%),radial-gradient(circle at 80% 18%,rgba(34,197,94,.12),transparent 26%);animation:qxSoftMove 9s ease-in-out infinite;pointer-events:none}.qx-command-lite>*{position:relative;z-index:1}
.qx-command-lite-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.qx-command-lite-card{border-radius:18px;padding:9px;background:rgba(255,255,255,.45);border:1px solid rgba(14,116,144,.12);transition:transform .18s ease,box-shadow .18s ease}.qx-command-lite-card:hover{transform:translateY(-3px);box-shadow:0 14px 28px rgba(2,132,199,.10)}.qx-command-lite-card b{display:block;font-size:10px;color:#075985;text-transform:uppercase;letter-spacing:.05em}.qx-command-lite-card span{display:block;margin-top:5px;font-weight:950;color:#0f172a;font-size:1rem}.qx-command-lite-title{font-weight:950;font-size:1.08rem;color:#0f172a;margin-bottom:8px}
.qx-home-pop-card,[data-testid="stExpander"]{animation:qxPopFloat .36s ease both}.qx-home-pop-card{margin:.45rem 0 .8rem;padding:10px;border-radius:26px;background:linear-gradient(135deg,rgba(255,255,255,.36),rgba(224,242,254,.20));border:1px solid rgba(255,255,255,.35);backdrop-filter:blur(24px) saturate(185%);box-shadow:0 18px 46px rgba(2,132,199,.10);position:relative;overflow:hidden}.qx-home-pop-card:before{content:"";position:absolute;inset:-38%;background:conic-gradient(from 120deg,transparent,rgba(56,189,248,.16),transparent,rgba(255,255,255,.22),transparent);animation:qxSpin 16s linear infinite;pointer-events:none}.qx-home-pop-card>*{position:relative;z-index:1}.qx-lowrev-shell [data-testid="stExpander"]{background:linear-gradient(135deg,rgba(240,253,250,.42),rgba(224,242,254,.22))!important;border-color:rgba(20,184,166,.18)!important}.qx-lowrev-shell div[data-testid="metric-container"]{background:linear-gradient(135deg,rgba(255,255,255,.58),rgba(240,253,250,.28))!important}
@keyframes qxPopFloat{from{opacity:0;transform:translateY(10px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}@keyframes qxSoftMove{0%,100%{transform:translate3d(0,0,0) rotate(0deg)}50%{transform:translate3d(2%,3%,0) rotate(8deg)}}
@media(max-width:760px){.qx-command-lite-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.qx-command-lite-card:last-child{grid-column:1/-1}.qx-home-pop-card{padding:7px;border-radius:22px}}
</style>
<script>
(function(){
  if(window.__qxCopyPatchInstalled) return;
  window.__qxCopyPatchInstalled=true;
  async function qxCopyText(txt){
    try{ await navigator.clipboard.writeText(txt); return true; }
    catch(e){
      try{
        const ta=document.createElement('textarea');
        ta.value=txt; ta.setAttribute('readonly',''); ta.style.position='fixed'; ta.style.left='-9999px';
        document.body.appendChild(ta); ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length);
        const ok=document.execCommand('copy'); ta.remove(); return ok;
      }catch(err){ return false; }
    }
  }
  window.qxCopyText=qxCopyText;
})();
</script>
""",
        unsafe_allow_html=True,
    )


def render_mobile_copy_button(label: str, text: str, key: str) -> None:
    """Self-contained phone-safe clipboard button with textarea fallback.

    Streamlit components run inside an iframe, so this helper does not depend on
    parent-window JS. It copies from the real tap event first, then falls back to
    a selected hidden textarea for older mobile browsers.
    """
    import json
    import re
    import streamlit.components.v1 as components

    safe_key = re.sub(r"[^A-Za-z0-9_-]", "_", str(key or "copy"))
    safe_label = html.escape(str(label or "Copy"))
    text_json = json.dumps(str(text or ""))
    components.html(
        f"""
        <style>
        :root{{--qx-blue:#0284c7;--qx-cyan:#06b6d4;--qx-teal:#14b8a6;--qx-ink:#0f172a;}}
        *{{box-sizing:border-box}}
        body{{margin:0;padding:0;background:transparent;font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;}}
        .qx-copy-wrap{{width:100%;padding:2px 0 0;}}
        .qx-copy-mobile-btn{{
          width:100%;min-height:54px;border:1px solid rgba(255,255,255,.55);border-radius:22px;cursor:pointer;
          font-weight:950;letter-spacing:.01em;color:white;font-size:15px;line-height:1.1;
          background:radial-gradient(circle at 12% 10%,rgba(255,255,255,.42),transparent 22%),linear-gradient(135deg,var(--qx-blue),var(--qx-cyan) 52%,var(--qx-teal));
          box-shadow:0 16px 34px rgba(2,132,199,.28),0 4px 12px rgba(20,184,166,.16),inset 0 1px 0 rgba(255,255,255,.52);
          position:relative;overflow:hidden;transition:transform .14s ease,box-shadow .14s ease,filter .14s ease;
          touch-action:manipulation;-webkit-tap-highlight-color:transparent;user-select:none;
        }}
        .qx-copy-mobile-btn:before{{content:"";position:absolute;inset:-80% -40%;background:linear-gradient(120deg,transparent,rgba(255,255,255,.58),transparent);transform:translateX(-78%) rotate(16deg);transition:transform .58s ease;pointer-events:none;}}
        .qx-copy-mobile-btn:after{{content:"Tap to copy • phone safe";display:block;font-size:11px;font-weight:850;opacity:.88;margin-top:4px;}}
        .qx-copy-mobile-btn:hover{{transform:translateY(-1px);filter:saturate(1.12);box-shadow:0 20px 42px rgba(2,132,199,.34),0 7px 16px rgba(20,184,166,.18),inset 0 1px 0 rgba(255,255,255,.58);}}
        .qx-copy-mobile-btn:hover:before{{transform:translateX(76%) rotate(16deg);}}
        .qx-copy-mobile-btn:active{{transform:scale(.982);}}
        .qx-copy-status{{min-height:20px;text-align:center;color:#075985;margin-top:6px;font-size:12px;font-weight:900;}}
        @media(max-width:520px){{.qx-copy-mobile-btn{{min-height:58px;border-radius:20px;font-size:14px;padding:10px 8px}}.qx-copy-mobile-btn:after{{font-size:10.5px}}}}
        </style>
        <div class="qx-copy-wrap">
          <button class="qx-copy-mobile-btn" id="qx_copy_{safe_key}" type="button">📋 {safe_label}</button>
          <textarea id="qx_copy_text_{safe_key}" readonly style="position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;opacity:.01;"></textarea>
          <div class="qx-copy-status" id="qx_copy_status_{safe_key}">Ready</div>
        </div>
        <script>
        (function(){{
          const btn=document.getElementById('qx_copy_{safe_key}');
          const ta=document.getElementById('qx_copy_text_{safe_key}');
          const status=document.getElementById('qx_copy_status_{safe_key}');
          const txt={text_json};
          ta.value=txt;
          async function copyNow(e){{
            if(e){{e.preventDefault(); e.stopPropagation();}}
            let ok=false;
            try{{
              if(navigator.clipboard && window.isSecureContext){{
                await navigator.clipboard.writeText(txt);
                ok=true;
              }}
            }}catch(err){{ ok=false; }}
            if(!ok){{
              try{{
                ta.style.left='0px'; ta.style.top='0px'; ta.style.width='2px'; ta.style.height='2px';
                ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length);
                ok=document.execCommand('copy');
                ta.blur(); ta.style.left='-9999px'; ta.style.top='-9999px';
              }}catch(err){{ ok=false; }}
            }}
            status.textContent = ok ? 'Copied ✅ Paste anywhere now.' : 'Copy blocked — fallback text is below. Long-press Select All.';
            if(ok){{ btn.textContent='✅ Copied successfully'; setTimeout(function(){{btn.textContent='📋 {safe_label}';}}, 1400); }}
            setTimeout(function(){{busy=false;}}, 350);
          }}
          btn.addEventListener('pointerup', copyNow, {{passive:false}});
          btn.addEventListener('click', copyNow, {{passive:false}});
          btn.addEventListener('touchend', copyNow, {{passive:false}});
        }})();
        </script>
        """,
        height=92,
    )



def render_pro_popup_layer() -> None:
    """Safe compatibility wrapper for the app runner.

    This keeps older runner imports working even when the visual popup layer is
    not available. It is UI-only and does not touch trading logic.
    """
    try:
        score = _num(st.session_state.get("last_reversal_score", st.session_state.get("reversal_score", 0)))
        if score >= 7:
            st.markdown(
                f'<div class="qx-alert-popup"><b>⚠ 10-Reversal danger: {int(score)}/10</b><span>Warning display only. Original decision logic is unchanged.</span></div>',
                unsafe_allow_html=True,
            )
    except Exception:
        return None


def render_pro_command_center_bar(active_tab: str = "") -> None:
    """Render a small command-center status bar expected by runner.py.

    Non-destructive: reads existing session_state only. If data is missing, it
    shows safe placeholders instead of crashing.
    """
    try:
        snap = _derive_snapshot() if "_derive_snapshot" in globals() else {}
        direction = html.escape(str(snap.get("direction", st.session_state.get("mini_bias", "WAIT"))))
        reversal = snap.get("reversal", st.session_state.get("last_reversal_score", st.session_state.get("reversal_score", 0)))
        adx = snap.get("adx", st.session_state.get("adx", st.session_state.get("last_adx", 0)))
        trust = snap.get("trust", st.session_state.get("trust", 0))
        tab = html.escape(str(active_tab or st.session_state.get("active_tab", "Home")))
        mode = html.escape(str(st.session_state.get("pro_terminal_market_mode", "calm")).upper())
        st.markdown(
            f"""
<div class="qx-command-lite">
  <div class="qx-command-lite-title">⚡ Command Center — {tab}</div>
  <div class="qx-command-lite-grid">
    <div class="qx-command-lite-card"><b>Bias</b><span>{direction}</span></div>
    <div class="qx-command-lite-card"><b>Reversal</b><span>{_fmt(reversal, 0)}/10</span></div>
    <div class="qx-command-lite-card"><b>ADX</b><span>{_fmt(adx, 1)}</span></div>
    <div class="qx-command-lite-card"><b>Trust</b><span>{_fmt(trust, 0)}%</span></div>
    <div class="qx-command-lite-card"><b>Mode</b><span>{mode}</span></div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    except Exception:
        # Never let an optional visual bar stop the app.
        return None

# 2026-06-09 lighter button state patch
try:
    from .pro_terminal_uiux_patch_20260609 import apply as _apply_pro_terminal_uiux_patch_20260609
    _apply_pro_terminal_uiux_patch_20260609(globals())
    del _apply_pro_terminal_uiux_patch_20260609
except Exception:
    pass


# 2026-06-15 long-term central copy engine override.
# All existing imports of core.pro_terminal_uiux.render_mobile_copy_button now
# route to ui.copy_tools.central_copy_button with a download/text fallback.
try:
    from ui.copy_tools import central_copy_button as _new7_central_copy_button_20260615
    def render_mobile_copy_button(label: str, text: str, key: str) -> None:  # type: ignore[no-redef]
        _new7_central_copy_button_20260615(label, text, key, show_fallback=True)
except Exception:
    pass
