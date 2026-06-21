"""2026-06-12 Research tab.

Final-year CS workspace for Data Analysis, Data Mining, and NLP.  Every heavy
calculation is manually run-gated so the mobile app stays light.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

UNIQUE = "20260612_research"


def _num(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else float(default)
    except Exception:
        return float(default)


def _optional_import(name: str):
    try:
        module = __import__(name)
        return True, getattr(module, "__version__", "installed")
    except Exception as exc:
        return False, str(exc).splitlines()[0][:80]


def _lib_status() -> pd.DataFrame:
    libs = [
        ("JavaScript helper", "streamlit_js_eval"),
        ("Polars", "polars"),
        ("DuckDB", "duckdb"),
        ("Numba", "numba"),
        ("PyArrow", "pyarrow"),
        ("Plotly Resampler", "plotly_resampler"),
        ("Streamlit Copy Button", "streamlit_copy_button"),
        ("CacheTools", "cachetools"),
        ("Scikit-learn", "sklearn"),
        ("LightGBM", "lightgbm"),
        ("CatBoost", "catboost"),
        ("Statsmodels", "statsmodels"),
        ("HMMLearn", "hmmlearn"),
        ("NLTK", "nltk"),
        ("VADER Sentiment", "vaderSentiment"),
    ]
    rows = []
    for label, mod in libs:
        ok, msg = _optional_import(mod)
        rows.append({"Library": label, "Import Name": mod, "Status": "READY" if ok else "OPTIONAL / NOT INSTALLED", "Version / Note": msg})
    return pd.DataFrame(rows)


def _prep_df(limit: int = 6000) -> pd.DataFrame:
    raw = st.session_state.get("dv_pp_df")
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        raw = st.session_state.get("last_df")
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        return pd.DataFrame()
    d = raw.copy().tail(int(limit)).reset_index(drop=True)
    low = {str(c).lower(): c for c in d.columns}
    ren = {"datetime": "time", "date": "time", "timestamp": "time", "o": "open", "h": "high", "l": "low", "c": "close"}
    for src, dst in ren.items():
        if src in low and dst not in d.columns:
            d = d.rename(columns={low[src]: dst})
    if "time" not in d.columns:
        d["time"] = pd.date_range(end=pd.Timestamp.now().floor("h"), periods=len(d), freq="h")
    for col in ["open", "high", "low", "close"]:
        if col not in d.columns:
            d[col] = d.get("close", np.nan)
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d["time"] = pd.to_datetime(d["time"], errors="coerce")
    return d.dropna(subset=["time", "close"]).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)


def _master_regime() -> str:
    for key in ("dv_pp_regime_summary", "final_merged_intelligence_pack_20260612", "lunch_5layer_powerbi_result"):
        obj = st.session_state.get(key, {})
        if isinstance(obj, dict):
            cur = obj.get("current_regime") or obj.get("master_regime")
            if cur:
                return str(cur)
    return "RANGE_NORMAL"


def _dir(regime: Any) -> str:
    s = str(regime).upper()
    if "BEAR" in s:
        return "SELL"
    if "BULL" in s:
        return "BUY"
    return "WAIT"


def _copy_button(label: str, text: str, key: str) -> None:
    try:
        from streamlit_copy_button import copy_button
        copy_button(text, label, key=key)
    except Exception:
        try:
            from core.pro_terminal_uiux import render_mobile_copy_button
            render_mobile_copy_button(label, text, key)
        except Exception:
            st.text_area(label, text, height=220, key=key + "_fallback")


def _analysis_pack(d: pd.DataFrame) -> Dict[str, Any]:
    if d.empty:
        return {"ok": False, "message": "No EURUSD H1 data loaded."}
    c = d["close"].astype(float)
    ret = c.pct_change().fillna(0)
    rng = (d["high"] - d["low"]).abs().replace(0, np.nan).ffill().fillna(c.abs() * 0.0005)
    desc = {
        "Rows": int(len(d)),
        "Last Time": str(d["time"].iloc[-1]),
        "Last Close": round(float(c.iloc[-1]), 5),
        "H1 Volatility pips": round(float(ret.tail(24).std()) * 10000, 3),
        "H4 Volatility pips": round(float(ret.rolling(4).sum().tail(42).std()) * 10000, 3),
        "D1 Volatility pips": round(float(ret.rolling(24).sum().tail(30).std()) * 10000, 3),
        "Avg Range pips": round(float(rng.tail(24).mean()) * 10000, 3),
        "Master Regime": _master_regime(),
        "Master Direction": _dir(_master_regime()),
    }
    # Optional Polars/DuckDB proof without making them required at runtime.
    engines = []
    try:
        import polars as pl
        pl.DataFrame(d.tail(48)).select(pl.col("close").mean())
        engines.append("Polars READY")
    except Exception:
        engines.append("Polars optional")
    try:
        import duckdb
        duckdb.sql("select avg(close) as avg_close from d").fetchall()
        engines.append("DuckDB READY")
    except Exception:
        engines.append("DuckDB optional")
    desc["Engine Alignment"] = ", ".join(engines)
    return {"ok": True, "summary": desc}


def _features(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    c = x["close"].astype(float)
    x["ret1"] = c.pct_change()
    x["ret3"] = c.pct_change(3)
    x["ret6"] = c.pct_change(6)
    x["ma12_gap"] = c / c.rolling(12).mean() - 1
    x["ma48_gap"] = c / c.rolling(48).mean() - 1
    x["range_pct"] = (x["high"] - x["low"]).abs() / c.replace(0, np.nan)
    x["vol24"] = x["ret1"].rolling(24).std()
    x["hour"] = pd.to_datetime(x["time"]).dt.hour
    x["target_up"] = (c.shift(-1) > c).astype(int)
    return x.dropna().reset_index(drop=True)


def _data_mining_pack(d: pd.DataFrame) -> Dict[str, Any]:
    if len(d) < 160:
        return {"ok": False, "message": "Need at least 160 H1 candles for research data mining."}
    f = _features(d).tail(3500)
    cols = ["ret1", "ret3", "ret6", "ma12_gap", "ma48_gap", "range_pct", "vol24", "hour"]
    split = max(80, int(len(f) * 0.78))
    train, test = f.iloc[:split], f.iloc[split:]
    master = _dir(_master_regime())
    rows: List[Dict[str, Any]] = []
    rf_summary: Dict[str, Any] = {"status": "scikit-learn optional"}
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score
        from sklearn.neighbors import NearestNeighbors
        model = RandomForestClassifier(n_estimators=80, max_depth=5, min_samples_leaf=8, random_state=42, n_jobs=1)
        model.fit(train[cols], train["target_up"])
        pred = model.predict(test[cols]) if len(test) else []
        acc = float(accuracy_score(test["target_up"], pred)) if len(test) else 0.0
        proba = float(model.predict_proba(f[cols].tail(1))[0][1])
        rf_dir = "BUY" if proba >= 0.55 else "SELL" if proba <= 0.45 else "WAIT"
        rf_summary = {"status": "READY", "Random Forest Accuracy %": round(acc * 100, 2), "RF Next 1H Up Probability %": round(proba * 100, 2), "RF Direction": rf_dir, "Master Direction": master, "RF Sync": "CONFIRM" if rf_dir == master else "CONFLICT" if rf_dir in ("BUY", "SELL") and master in ("BUY", "SELL") else "NEUTRAL"}
        nn = NearestNeighbors(n_neighbors=min(14, len(f) - 2), metric="euclidean")
        z = (f[cols] - f[cols].mean()) / f[cols].std().replace(0, 1)
        nn.fit(z.iloc[:-1])
        dist, idx = nn.kneighbors(z.tail(1), return_distance=True)
        for rank, (i, di) in enumerate(zip(idx[0], dist[0]), 1):
            row = f.iloc[int(i)]
            next_move = float(f["close"].iloc[min(int(i) + 1, len(f) - 1)] - row["close"])
            hist_dir = "BUY" if next_move > 0 else "SELL" if next_move < 0 else "WAIT"
            score = 100 - min(70, float(di) * 14)
            label = f"{master} allowed" if hist_dir == master and score >= 55 else "WATCH / WAIT"
            rows.append({"Priority Rank": rank, "Hour": int(row["hour"]), "Similarity Score": round(score, 2), "Historical Next 1H Dir": hist_dir, "Historical Move pips": round(next_move * 10000, 2), "Master Direction": master, "Prescriptive Label": label, "Reason": "KNN similar row + RF support"})
    except Exception as exc:
        rf_summary["error"] = str(exc)[:160]
    pr = pd.DataFrame(rows)
    if not pr.empty:
        pr = pr.sort_values(["Priority Rank"], ascending=True).reset_index(drop=True)
    return {"ok": True, "random_forest": rf_summary, "knn_priority": pr}


def _fetch_news(finnhub: str, fmp: str, limit: int) -> Tuple[List[Dict[str, Any]], str]:
    if finnhub:
        try:
            r = requests.get("https://finnhub.io/api/v1/news", params={"category": "forex", "token": finnhub}, timeout=8)
            r.raise_for_status()
            rows = r.json()
            if isinstance(rows, list) and rows:
                return rows[:limit], "Finnhub"
        except Exception:
            pass
    if fmp:
        try:
            r = requests.get("https://financialmodelingprep.com/stable/news/forex", params={"apikey": fmp, "limit": limit}, timeout=8)
            r.raise_for_status()
            rows = [{"headline": x.get("title"), "summary": x.get("text"), "publishedDate": x.get("publishedDate"), "source": x.get("site")} for x in r.json()[:limit]]
            if rows:
                return rows, "FMP"
        except Exception:
            pass
    rows = []
    for url in ["https://www.forexlive.com/feed/news/", "https://www.fxstreet.com/rss/news"]:
        try:
            r = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for it in root.findall(".//item"):
                rows.append({"headline": it.findtext("title") or "", "summary": it.findtext("description") or "", "publishedDate": it.findtext("pubDate") or "", "source": url.split("/")[2]})
                if len(rows) >= limit:
                    return rows, "RSS"
        except Exception:
            pass
    return rows, "RSS"


def _score_news(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        vader = SentimentIntensityAnalyzer()
    except Exception:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            vader = SentimentIntensityAnalyzer()
        except Exception:
            vader = None
    kw = ("eurusd", "eur/usd", "euro", "eurozone", "ecb", "fed", "dollar", "usd", "cpi", "nfp", "pmi", "inflation", "yield")
    eur_pos, eur_neg = ("euro rises", "euro stronger", "ecb hawkish", "pmi beat", "spanish inflation picks up", "french inflation accelerates", "germany inflation picked up", "core inflation"), ("euro falls", "euro weaker", "ecb dovish", "pmi miss", "recession", "political risk")
    usd_pos, usd_neg = ("dollar rises", "dollar stronger", "fed hawkish", "nfp beat", "cpi hot", "yields rise", "iran", "middle east conflict", "safe haven"), ("dollar falls", "dollar weaker", "fed cut", "fed dovish", "nfp miss", "cpi cool", "deal optimism", "risk rally")
    out = []
    for r in rows:
        text = (str(r.get("headline") or "") + " " + str(r.get("summary") or "")).lower()
        if not any(k in text for k in kw):
            continue
        sent = float(vader.polarity_scores(text).get("compound", 0.0)) if vader else 0.0
        eur = sum(1.25 for p in eur_pos if p in text) - sum(1.25 for p in eur_neg if p in text) + sent * 0.25
        usd = sum(1.25 for p in usd_pos if p in text) - sum(1.25 for p in usd_neg if p in text) - sent * 0.10
        if any(w in text for w in ["euro", "eurozone", "european", "ecb", "german", "french", "spanish"]):
            eur += 0.18
        if any(w in text for w in ["dollar", "usd", "fed", "treasury", "yield", " nfp", " cpi"]):
            usd += 0.18
        if any(w in text for w in ["iran", "geopolitical", "conflict", "oil", "safe haven"]):
            usd += 0.45
        delta = eur - usd
        nd = "BUY" if delta > 0.35 else "SELL" if delta < -0.35 else "WAIT"
        out.append({"Priority Rank": len(out)+1, "Title": str(r.get("headline") or "")[:160], "Source": str(r.get("source") or "news"), "EUR Impact": round(eur, 2), "USD Impact": round(usd, 2), "VADER": round(sent, 3), "News Direction": nd, "Static Impact": "BUY support" if nd=="BUY" else "SELL support" if nd=="SELL" else "WAIT / mixed", "Published": str(r.get("publishedDate") or "")[:35]})
    df = pd.DataFrame(out[:30])
    if not df.empty:
        df["Impact Abs"] = (pd.to_numeric(df["EUR Impact"], errors="coerce").fillna(0) - pd.to_numeric(df["USD Impact"], errors="coerce").fillna(0)).abs()
        df = df.sort_values(["Impact Abs", "Priority Rank"], ascending=[False, True]).reset_index(drop=True)
        df["Priority Rank"] = df.index + 1
        df = df.drop(columns=["Impact Abs"], errors="ignore")
    master = _dir(_master_regime())
    if df.empty:
        summary = {"News Direction": "WAIT", "News Sync": "LOW PRIORITY", "Articles Used": 0, "Master Direction": master}
    else:
        eur = pd.to_numeric(df["EUR Impact"], errors="coerce").fillna(0).mean()
        usd = pd.to_numeric(df["USD Impact"], errors="coerce").fillna(0).mean()
        nd = "BUY" if eur - usd > 0.25 else "SELL" if eur - usd < -0.25 else "WAIT"
        sync = "CONFIRM" if nd == master and nd != "WAIT" else "CONFLICT" if nd in ("BUY", "SELL") and master in ("BUY", "SELL") and nd != master else "NEUTRAL"
        summary = {"News Direction": nd, "News Sync": sync, "Articles Used": int(len(df)), "Master Direction": master, "Avg EUR Impact": round(float(eur), 3), "Avg USD Impact": round(float(usd), 3)}
    return {"summary": summary, "table": df}


def _regime_nlp_history(d: pd.DataFrame, news_summary: Dict[str, Any]) -> pd.DataFrame:
    if d.empty:
        return pd.DataFrame()
    x = d.tail(25 * 24).copy()
    x["hour"] = pd.to_datetime(x["time"]).dt.hour
    x = x[(x["hour"] >= 1) & (x["hour"] <= 14)].copy()
    if x.empty:
        return pd.DataFrame()
    c = x["close"].astype(float)
    x["ma12"] = c.rolling(12, min_periods=3).mean()
    x["ma48"] = c.rolling(48, min_periods=10).mean()
    x["Regime Direction"] = np.where(x["ma12"] > x["ma48"], "BUY", np.where(x["ma12"] < x["ma48"], "SELL", "WAIT"))
    master = _dir(_master_regime())
    news_sync = news_summary.get("News Sync", "NEUTRAL")
    x["Greedy Score"] = np.where(x["Regime Direction"] == master, 68, 42) + (12 if news_sync == "CONFIRM" else -14 if news_sync == "CONFLICT" else 0)
    x["Entry Opportunity"] = np.where((x["Greedy Score"] >= 64) & (x["Regime Direction"] == master), "YES", "WATCH")
    keep = x.tail(120).sort_values(["Greedy Score", "time"], ascending=[False, False]).head(14).copy()
    keep = keep.reset_index(drop=True)
    keep["Priority Rank"] = keep.index + 1
    return keep[["Priority Rank", "time", "hour", "Regime Direction", "Greedy Score", "Entry Opportunity"]]


def _run_research(finnhub: str, fmp: str, news_limit: int) -> Dict[str, Any]:
    d = _prep_df(6000)
    analysis = _analysis_pack(d)
    mining = _data_mining_pack(d)
    rows, source = _fetch_news(str(finnhub or "").strip(), str(fmp or "").strip(), int(news_limit))
    nlp = _score_news(rows)
    nlp["source"] = source
    hist = _regime_nlp_history(d, nlp.get("summary", {}))
    pack = {"export_type": "RESEARCH_DATA_ANALYSIS_MINING_NLP_20260612", "built_at": str(pd.Timestamp.now()), "symbol": "EURUSD", "timeframe": "H1", "library_status": _lib_status(), "data_analysis": analysis, "data_mining": mining, "nlp": nlp, "regime_nlp_history": hist}
    text = json.dumps(_safe(pack), indent=2, ensure_ascii=False, default=str)
    st.session_state["research_pack_20260612"] = pack
    st.session_state["research_export_20260612"] = text
    return pack


def _safe(obj: Any) -> Any:
    if isinstance(obj, pd.DataFrame):
        return obj.head(200).to_dict("records")
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(x) for x in obj[:200]]
    return obj


def _render_pack(pack: Dict[str, Any]) -> None:
    st.markdown("### 🎓 Research Workspace Result")
    tabs = st.tabs(["Data Analysis", "Data Mining", "NLP", "Library Status", "Copy"])
    with tabs[0]:
        st.subheader("Descriptive Data Analysis")
        try:
            from tabs.dinner_morning_data_patch_20260614 import render_data_analysis_result_table_20260614
            render_data_analysis_result_table_20260614("research_data_analysis")
        except Exception as _analysis_table_exc_20260614:
            st.caption(f"Current result table skipped safely: {_analysis_table_exc_20260614}")
        summ = pack.get("data_analysis", {}).get("summary", {})
        if summ:
            cols = st.columns(4)
            cols[0].metric("Rows", summ.get("Rows", "-"))
            cols[1].metric("Last Close", summ.get("Last Close", "-"))
            cols[2].metric("Master Regime", summ.get("Master Regime", "-"))
            cols[3].metric("Master Direction", summ.get("Master Direction", "-"))
            st.json(summ)
        else:
            st.info(pack.get("data_analysis", {}).get("message", "No analysis yet."))
    with tabs[1]:
        st.subheader("Data Mining: Random Forest + KNN Priority")
        mining = pack.get("data_mining", {})
        st.json(mining.get("random_forest", {}))
        pr = mining.get("knn_priority", pd.DataFrame())
        if isinstance(pr, pd.DataFrame) and not pr.empty:
            st.dataframe(pr, use_container_width=True, hide_index=True, height=320)
        with st.expander("Open / Close — Mirrored Home/Data Visualization mining logic", expanded=False):
            merged = st.session_state.get("final_merged_intelligence_pack_20260612", {})
            if isinstance(merged, dict) and merged:
                st.caption("These are related mining/priority outputs mirrored here for CS practice. Original Home/Data Visualization logic remains in place.")
                st.json({"master_regime": merged.get("master_regime"), "master_direction": merged.get("master_direction"), "market_story": merged.get("market_story")})
                mp = merged.get("knn_greedy_priority", pd.DataFrame())
                if isinstance(mp, pd.DataFrame) and not mp.empty:
                    st.dataframe(mp, use_container_width=True, hide_index=True, height=260)
            else:
                st.info("Run Data Visualization → Final Merged Intelligence to mirror more mining logic here.")
    with tabs[2]:
        st.subheader("NLP: EURUSD News Confirmation + Regime History")
        nlp = pack.get("nlp", {})
        st.json(nlp.get("summary", {}))
        nt = nlp.get("table", pd.DataFrame())
        if isinstance(nt, pd.DataFrame) and not nt.empty:
            st.dataframe(nt, use_container_width=True, hide_index=True, height=260)
        hist = pack.get("regime_nlp_history", pd.DataFrame())
        if isinstance(hist, pd.DataFrame) and not hist.empty:
            st.markdown("#### Regime Prediction History + NLP — priority 1 to 14")
            st.dataframe(hist, use_container_width=True, hide_index=True, height=320)
    with tabs[3]:
        ls = pack.get("library_status", pd.DataFrame())
        if isinstance(ls, pd.DataFrame):
            st.dataframe(ls, use_container_width=True, hide_index=True, height=420)
    with tabs[4]:
        text = st.session_state.get("research_export_20260612", json.dumps(_safe(pack), indent=2, default=str))
        _copy_button("Copy Research Full", text, f"copy_research_full_{UNIQUE}")
        _copy_button("Copy Research Necessary 100 Lines", "\n".join(text.splitlines()[:100]), f"copy_research_100_{UNIQUE}")


def show() -> None:
    st.markdown("# 🎓 Research")
    st.caption("For CS final-year practice: Data Analysis, Data Mining, and NLP using your existing EURUSD H1 data. Everything is run-gated.")
    c = st.columns([1, 1, 1, 1])
    if c[0].button("▶ Run Research Calculation", use_container_width=True, key=f"run_{UNIQUE}"):
        st.session_state["research_run_calculate"] = True
    if c[1].button("⏸ Stop / Lock", use_container_width=True, key=f"stop_{UNIQUE}"):
        st.session_state["research_run_calculate"] = False
    finnhub = c[2].text_input("Finnhub API key", value=st.session_state.get("research_finnhub_key", ""), type="password", key=f"finnhub_{UNIQUE}")
    fmp = c[3].text_input("FMP API backup", value=st.session_state.get("research_fmp_key", ""), type="password", key=f"fmp_{UNIQUE}")
    st.session_state["research_finnhub_key"] = finnhub
    st.session_state["research_fmp_key"] = fmp
    st.info("Research tab mirrors Home/Data Visualization logic only when useful. It does not override Unified PowerBI direction.")
    selected = st.radio("Research inner tab", ["Data Analysis", "Data Mining", "NLP"], horizontal=True, key=f"inner_{UNIQUE}")
    st.session_state["research_inner_tab"] = selected
    if not bool(st.session_state.get("research_run_calculate", False)):
        with st.expander("Open / Close — Research waiting", expanded=True):
            st.write("Press **Run Research Calculation** first. No data mining or NLP API/RSS call runs on page open.")
            st.dataframe(_lib_status(), use_container_width=True, hide_index=True, height=260)
        return
    if st.button("🔄 Build / Refresh Research Pack", use_container_width=True, key=f"build_{UNIQUE}"):
        with st.spinner("Building Data Analysis + Data Mining + NLP research pack…"):
            _run_research(finnhub, fmp, 20)
    if "research_pack_20260612" not in st.session_state:
        with st.spinner("First research run…"):
            _run_research(finnhub, fmp, 20)
    _render_pack(st.session_state.get("research_pack_20260612", {}))
