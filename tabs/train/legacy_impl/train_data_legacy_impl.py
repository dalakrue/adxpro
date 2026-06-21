import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from core.ui.compact import render_metric_cards
from core.global_upgrade import render_page_shell, render_tab_footer

from core.database import append_csv, read_csv, save_market_cache
from core.quant_models import add_indicators, quant_stack, trend_math_snapshot

try:
    from core.ui_helpers import choice_buttons
except Exception:
    def choice_buttons(label, options, key, columns=4, default=None, help_text=""):
        options = list(options or [])
        if not options:
            return ""
        return st.radio(label, options, key=key, index=options.index(default) if default in options else 0)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, precision_score, recall_score
except Exception:
    RandomForestClassifier = None
    accuracy_score = precision_score = recall_score = None


FEATURE_COLS = [
    "adx", "plus_di", "minus_di", "atr", "pressure", "adx_slope", "ret", "momentum",
    "volatility", "vol_decay", "fat_tail", "mean_dist", "wick_ratio", "range_expansion",
    "directional_efficiency", "exhaustion_risk", "start_impulse_score", "trend_power",
]


def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def _normalize_df(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.copy()
    rename = {c: str(c).strip().lower() for c in out.columns}
    out = out.rename(columns=rename)
    if "datetime" in out.columns and "time" not in out.columns:
        out = out.rename(columns={"datetime": "time"})
    if "timestamp" in out.columns and "time" not in out.columns:
        out = out.rename(columns={"timestamp": "time"})
    if "time" in out.columns:
        out["time"] = pd.to_datetime(out["time"], errors="coerce")
        out = out.dropna(subset=["time"]).sort_values("time").drop_duplicates("time", keep="last")
    for c in ["open", "high", "low", "close", "volume"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    required = [c for c in ["open", "high", "low", "close"] if c in out.columns]
    if required:
        out = out.dropna(subset=required)
    return out.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def _load_training_cache():
    cache = read_csv("training_data_cache", limit=250000)
    return _normalize_df(cache)


def _prepare_training_frame(df, horizon=12, min_move_atr=0.15):
    df = _normalize_df(df)
    if df.empty or len(df) < 30:
        return pd.DataFrame()
    try:
        out = add_indicators(df.copy())
    except Exception:
        out = df.copy()
    out = _normalize_df(out)
    if out.empty or "close" not in out.columns:
        return pd.DataFrame()

    horizon = int(max(1, horizon))
    out["future_close"] = out["close"].shift(-horizon)
    out["future_move"] = out["future_close"] - out["close"]
    out["future_move_pct"] = out["future_move"] / out["close"].replace(0, np.nan) * 100
    atr = pd.to_numeric(out.get("atr", 0), errors="coerce").replace(0, np.nan)
    out["future_move_atr"] = out["future_move"] / atr
    out["target_buy"] = (out["future_move_atr"] > float(min_move_atr)).astype(int)
    out["target_sell"] = (out["future_move_atr"] < -float(min_move_atr)).astype(int)
    out["target_direction"] = np.where(out["target_buy"] == 1, "BUY", np.where(out["target_sell"] == 1, "SELL", "WAIT"))
    out["train_source"] = st.session_state.get("source", "UNKNOWN")
    out["symbol"] = st.session_state.get("symbol", "XAUUSD")
    out["timeframe"] = st.session_state.get("timeframe", "M1")
    out["prepared_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    out = out.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    return out.reset_index(drop=True)


def _merge_training(existing, new_rows):
    frames = []
    for f in [existing, new_rows]:
        f = _normalize_df(f)
        if not f.empty:
            frames.append(f)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    for c in ["symbol", "timeframe"]:
        if c not in combined.columns:
            combined[c] = st.session_state.get(c, "XAUUSD" if c == "symbol" else "M1")
    if "time" in combined.columns:
        combined["time"] = pd.to_datetime(combined["time"], errors="coerce")
        combined = combined.dropna(subset=["time"]).sort_values("time")
        combined = combined.drop_duplicates(["symbol", "timeframe", "time"], keep="last")
    return combined.tail(250000).reset_index(drop=True)


def _collect_training_rows(df, label="AUTO", horizon=12, min_move_atr=0.15):
    prepared = _prepare_training_frame(df, horizon=horizon, min_move_atr=min_move_atr)
    if prepared.empty:
        return 0
    prepared["collect_label"] = label
    existing = st.session_state.get("training_df")
    combined = _merge_training(existing, prepared)
    st.session_state.training_df = combined
    st.session_state.training_rows = combined.tail(5000).to_dict("records")
    return len(prepared)


def _quality_report(df):
    df = _normalize_df(df)
    if df.empty:
        return {"status": "NO DATA", "score": 0, "rows": 0, "issues": ["No market dataframe found."]}
    issues = []
    needed = ["time", "open", "high", "low", "close"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        issues.append("Missing columns: " + ", ".join(missing))
    if "time" in df.columns:
        dup = int(df["time"].duplicated().sum())
        if dup:
            issues.append(f"Duplicate candles: {dup}")
        gaps = df["time"].diff().dropna()
        if not gaps.empty:
            med = gaps.median()
            big_gaps = int((gaps > med * 3).sum()) if med > pd.Timedelta(0) else 0
            if big_gaps:
                issues.append(f"Large time gaps: {big_gaps}")
    for c in ["open", "high", "low", "close"]:
        if c in df.columns:
            bad = int(pd.to_numeric(df[c], errors="coerce").isna().sum())
            if bad:
                issues.append(f"Bad {c} values: {bad}")
    score = max(0, 100 - len(issues) * 18)
    status = "GOOD" if score >= 80 else "CHECK" if score >= 50 else "BAD"
    return {"status": status, "score": score, "rows": len(df), "issues": issues or ["No critical data-quality issue detected."]}


def _train_validation(df):
    df = _normalize_df(df)
    if df.empty or len(df) < 120:
        return None, "Need at least about 120 prepared rows for validation."
    if RandomForestClassifier is None:
        return None, "scikit-learn is not installed, so model validation is unavailable."
    if "target_buy" not in df.columns:
        return None, "Prepared labels are missing. Collect/prepare data first."
    features = [c for c in FEATURE_COLS if c in df.columns]
    if len(features) < 6:
        return None, "Not enough feature columns for training validation."
    work = df.dropna(subset=features + ["target_buy"]).copy()
    work = work.iloc[:-12] if len(work) > 140 else work
    if len(work) < 100 or work["target_buy"].nunique() < 2:
        return None, "Not enough BUY/SELL variation in labels yet."
    split = int(len(work) * 0.78)
    X_train = work[features].iloc[:split].replace([np.inf, -np.inf], 0).fillna(0)
    y_train = work["target_buy"].iloc[:split].astype(int)
    X_test = work[features].iloc[split:].replace([np.inf, -np.inf], 0).fillna(0)
    y_test = work["target_buy"].iloc[split:].astype(int)
    if len(X_test) < 10:
        return None, "Test sample is too small."
    model = RandomForestClassifier(n_estimators=220, max_depth=8, min_samples_leaf=4, random_state=19, n_jobs=-1)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    last_x = work[features].tail(1).replace([np.inf, -np.inf], 0).fillna(0)
    last_buy_prob = float(model.predict_proba(last_x)[0][1])
    importances = pd.DataFrame({"feature": features, "importance": model.feature_importances_}).sort_values("importance", ascending=False)
    metrics = {
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "accuracy": round(float(accuracy_score(y_test, pred)) * 100, 2),
        "precision": round(float(precision_score(y_test, pred, zero_division=0)) * 100, 2),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)) * 100, 2),
        "last_buy_probability": round(last_buy_prob * 100, 2),
        "last_sell_probability": round((1 - last_buy_prob) * 100, 2),
        "bias": "BUY" if last_buy_prob >= 0.55 else "SELL" if last_buy_prob <= 0.45 else "WAIT",
        "avg_test_buy_probability": round(float(np.mean(proba)) * 100, 2),
    }
    return (metrics, importances), "OK"


def _auto_save_training_result(train_df, live_df):
    try:
        target = train_df if isinstance(train_df, pd.DataFrame) and not train_df.empty else live_df
        if target is None or not isinstance(target, pd.DataFrame) or target.empty:
            return
        now = pd.Timestamp.now()
        last = st.session_state.get("train_last_auto_db_save_time")
        should = True if last is None else (now - pd.to_datetime(last)).total_seconds() >= 60
        if not should:
            return
        save_market_cache(target, name="training_data_cache", max_rows=50000)
        append_csv("training_snapshots", {
            "time": now,
            "reason": "auto_train_save",
            "symbol": st.session_state.get("symbol", "XAUUSD"),
            "timeframe": st.session_state.get("timeframe", "M1"),
            "source": st.session_state.get("source", "UNKNOWN"),
            "rows": int(len(target)),
            "first_time": str(target["time"].min()) if "time" in target.columns else "",
            "last_time": str(target["time"].max()) if "time" in target.columns else "",
        })
        st.session_state.train_last_auto_db_save_time = now
    except Exception:
        pass


def _history_search_panel(df):
    st.markdown("### 📅 History Search by Day")
    if df is None or df.empty or "time" not in df.columns:
        st.info("No time-based training data loaded yet.")
        return
    tmp = _normalize_df(df)
    if tmp.empty:
        st.info("Loaded data has no valid time column.")
        return
    min_day = tmp["time"].min().date()
    max_day = tmp["time"].max().date()
    chosen = st.date_input("Choose day to inspect", value=max_day, min_value=min_day, max_value=max_day, key="train_history_day")
    day_df = tmp[tmp["time"].dt.date == chosen]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(day_df))
    if not day_df.empty:
        c2.metric("Open", round(float(day_df["open"].iloc[0]), 5) if "open" in day_df.columns else "N/A")
        c3.metric("Close", round(float(day_df["close"].iloc[-1]), 5) if "close" in day_df.columns else "N/A")
        if "close" in day_df.columns:
            change = (day_df["close"].iloc[-1] - day_df["close"].iloc[0]) / max(abs(day_df["close"].iloc[0]), 1e-9) * 100
            c4.metric("Day Change %", round(float(change), 4))
            st.line_chart(day_df.set_index("time")[["close"]])
        with st.expander("📋 Open raw day data", expanded=False):
            st.dataframe(day_df.tail(1500), use_container_width=True, height=360)
    else:
        st.warning("No candles found for that day in the loaded dataset.")


def _source_frame():
    live = _normalize_df(st.session_state.get("last_df"))
    cache = _load_training_cache()
    if not live.empty:
        return live, cache, "shared live data"
    if not cache.empty:
        return cache, cache, "saved training cache"
    return pd.DataFrame(), cache, "empty"




def _session_name(ts):
    try:
        h = pd.to_datetime(ts).hour
    except Exception:
        return "UNKNOWN"
    if 0 <= h < 7:
        return "Asia early"
    if 7 <= h < 12:
        return "Asia late"
    if 12 <= h < 16:
        return "London open"
    if 16 <= h < 21:
        return "London/NY mix"
    return "NY late"


def _add_train_regime_columns(df):
    df = _normalize_df(df)
    if df.empty:
        return df
    out = df.copy()
    if "time" in out.columns:
        out["session_bucket"] = out["time"].apply(_session_name)
        out["hour"] = pd.to_datetime(out["time"], errors="coerce").dt.hour.fillna(-1).astype(int)
    if "target_direction" in out.columns:
        out["is_trade_label"] = out["target_direction"].isin(["BUY", "SELL"]).astype(int)
    if "adx" in out.columns:
        adx = pd.to_numeric(out["adx"], errors="coerce").fillna(0)
        out["regime_strength"] = np.where(adx >= 30, "STRONG", np.where(adx >= 20, "ACTIVE", "WEAK"))
    if "pressure" in out.columns:
        pressure = pd.to_numeric(out["pressure"], errors="coerce").fillna(0)
        out["pressure_side"] = np.where(pressure > 0, "BUY_PRESSURE", np.where(pressure < 0, "SELL_PRESSURE", "FLAT"))
    return out


def _label_balance_report(df):
    df = _add_train_regime_columns(df)
    if df.empty or "target_direction" not in df.columns:
        return pd.DataFrame()
    total = max(len(df), 1)
    rep = df["target_direction"].value_counts(dropna=False).rename_axis("label").reset_index(name="rows")
    rep["percent"] = (rep["rows"] / total * 100).round(2)
    return rep


def _session_edge_report(df):
    df = _add_train_regime_columns(df)
    if df.empty or "session_bucket" not in df.columns or "target_direction" not in df.columns:
        return pd.DataFrame()
    g = df.groupby(["session_bucket", "target_direction"], dropna=False).size().reset_index(name="rows")
    pivot = g.pivot_table(index="session_bucket", columns="target_direction", values="rows", fill_value=0).reset_index()
    for col in ["BUY", "SELL", "WAIT"]:
        if col not in pivot.columns:
            pivot[col] = 0
    total = pivot[["BUY", "SELL", "WAIT"]].sum(axis=1).replace(0, np.nan)
    pivot["buy_pct"] = (pivot["BUY"] / total * 100).round(2).fillna(0)
    pivot["sell_pct"] = (pivot["SELL"] / total * 100).round(2).fillna(0)
    pivot["trade_rows"] = pivot["BUY"] + pivot["SELL"]
    pivot["edge"] = np.where(pivot["buy_pct"] >= pivot["sell_pct"], "BUY", "SELL")
    pivot["edge_gap_pct"] = (pivot["buy_pct"] - pivot["sell_pct"]).abs().round(2)
    return pivot.sort_values(["edge_gap_pct", "trade_rows"], ascending=False)


def _feature_health_report(df):
    df = _normalize_df(df)
    rows = []
    if df.empty:
        return pd.DataFrame()
    for col in FEATURE_COLS:
        if col in df.columns:
            ser = pd.to_numeric(df[col], errors="coerce")
            rows.append({
                "feature": col,
                "missing_pct": round(float(ser.isna().mean() * 100), 2),
                "zero_pct": round(float((ser.fillna(0) == 0).mean() * 100), 2),
                "mean": round(float(ser.replace([np.inf, -np.inf], np.nan).mean()), 6) if ser.notna().any() else 0,
                "std": round(float(ser.replace([np.inf, -np.inf], np.nan).std()), 6) if ser.notna().sum() > 1 else 0,
                "usable": "YES" if ser.notna().sum() >= 50 and ser.nunique(dropna=True) > 3 else "CHECK",
            })
    return pd.DataFrame(rows)


def _train_multiclass_validation(df):
    df = _add_train_regime_columns(df)
    if df.empty or len(df) < 160:
        return None, "Need at least about 160 prepared rows for 3-side validation."
    if RandomForestClassifier is None:
        return None, "scikit-learn is not installed, so model validation is unavailable."
    if "target_direction" not in df.columns:
        return None, "Prepared direction labels are missing."
    features = [c for c in FEATURE_COLS if c in df.columns]
    if len(features) < 6:
        return None, "Not enough feature columns for 3-side training."
    work = df.dropna(subset=features + ["target_direction"]).copy()
    work = work[work["target_direction"].isin(["BUY", "SELL", "WAIT"])]
    if len(work) < 140 or work["target_direction"].nunique() < 2:
        return None, "Not enough label variation yet."
    # Drop the newest horizon-like tail to reduce look-ahead leakage in validation.
    work = work.iloc[:-12] if len(work) > 180 else work
    split = int(len(work) * 0.78)
    X_train = work[features].iloc[:split].replace([np.inf, -np.inf], 0).fillna(0)
    y_train = work["target_direction"].iloc[:split].astype(str)
    X_test = work[features].iloc[split:].replace([np.inf, -np.inf], 0).fillna(0)
    y_test = work["target_direction"].iloc[split:].astype(str)
    if len(X_test) < 12:
        return None, "Test sample is too small."
    model = RandomForestClassifier(n_estimators=260, max_depth=9, min_samples_leaf=4, random_state=42, n_jobs=-1, class_weight="balanced")
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    classes = list(model.classes_)
    last_x = work[features].tail(1).replace([np.inf, -np.inf], 0).fillna(0)
    probs = dict(zip(classes, model.predict_proba(last_x)[0]))
    buy_p = float(probs.get("BUY", 0.0))
    sell_p = float(probs.get("SELL", 0.0))
    wait_p = float(probs.get("WAIT", 0.0))
    top_label = max({"BUY": buy_p, "SELL": sell_p, "WAIT": wait_p}, key={"BUY": buy_p, "SELL": sell_p, "WAIT": wait_p}.get)
    metrics = {
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "accuracy": round(float(accuracy_score(y_test, pred)) * 100, 2),
        "buy_probability": round(buy_p * 100, 2),
        "sell_probability": round(sell_p * 100, 2),
        "wait_probability": round(wait_p * 100, 2),
        "bias": top_label,
        "confidence_gap": round((max(buy_p, sell_p, wait_p) - sorted([buy_p, sell_p, wait_p])[-2]) * 100, 2),
    }
    importances = pd.DataFrame({"feature": features, "importance": model.feature_importances_}).sort_values("importance", ascending=False)
    pred_df = pd.DataFrame({"actual": y_test.values, "predicted": pred})
    conf = pd.crosstab(pred_df["actual"], pred_df["predicted"], dropna=False)
    return (metrics, importances, conf), "OK"


def _render_learning_memory(train_df):
    st.markdown("### 🧩 Learning Memory")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Memory rows", f"{len(train_df):,}")
    first = str(train_df["time"].min()) if "time" in train_df.columns and not train_df.empty else "N/A"
    last = str(train_df["time"].max()) if "time" in train_df.columns and not train_df.empty else "N/A"
    c2.metric("First candle", first[:19])
    c3.metric("Last candle", last[:19])
    c4.metric("Unique days", int(train_df["time"].dt.date.nunique()) if "time" in train_df.columns and not train_df.empty else 0)


def _save_model_snapshot(metrics, importances):
    try:
        append_csv("training_model_snapshots", {
            "time": pd.Timestamp.now(),
            "symbol": st.session_state.get("symbol", "XAUUSD"),
            "timeframe": st.session_state.get("timeframe", "M1"),
            "bias": metrics.get("bias"),
            "buy_probability": metrics.get("buy_probability", metrics.get("last_buy_probability")),
            "sell_probability": metrics.get("sell_probability", metrics.get("last_sell_probability")),
            "wait_probability": metrics.get("wait_probability", ""),
            "accuracy": metrics.get("accuracy"),
            "train_rows": metrics.get("train_rows"),
            "test_rows": metrics.get("test_rows"),
            "top_features": ", ".join(importances.head(5)["feature"].astype(str).tolist()) if isinstance(importances, pd.DataFrame) and not importances.empty else "",
        })
        return True
    except Exception:
        return False



# -----------------------------
# 2026-06-01 Train Data Pro+ additive upgrade
# -----------------------------
def _training_readiness_score(train_df):
    """Return a simple readiness score so the tab can tell the user whether the data is useful yet."""
    df = _add_train_regime_columns(train_df)
    if df.empty:
        return {"score": 0, "status": "NO DATA", "reasons": ["No training memory rows yet."]}
    reasons = []
    score = 0
    rows = len(df)
    if rows >= 5000:
        score += 30
    elif rows >= 1000:
        score += 22
    elif rows >= 250:
        score += 12
    else:
        reasons.append("Collect more rows; 1,000+ is better and 5,000+ is safer.")
    if "time" in df.columns and df["time"].dt.date.nunique() >= 3:
        score += 18
    else:
        reasons.append("More than one market day improves generalization.")
    if "target_direction" in df.columns:
        vc = df["target_direction"].value_counts(normalize=True)
        if len(vc) >= 2 and float(vc.max()) <= 0.82:
            score += 20
        else:
            reasons.append("Labels are one-sided; adjust horizon/min ATR or collect different sessions.")
    feats = _feature_health_report(df)
    if not feats.empty:
        usable = float((feats.get("usable") == "YES").mean())
        score += int(20 * usable)
        if usable < 0.65:
            reasons.append("Several features are flat or missing.")
    if "session_bucket" in df.columns and df["session_bucket"].nunique() >= 3:
        score += 12
    else:
        reasons.append("Collect Asia, London, London/NY mix, and NY rows for better session edge.")
    status = "READY" if score >= 75 else "IMPROVING" if score >= 45 else "EARLY"
    return {"score": int(min(score, 100)), "status": status, "reasons": reasons or ["Training memory is usable for research validation."]}


def _build_exit_training_labels(df, adverse_atr=0.35, favorable_atr=0.25, horizon=12):
    """Add exit-oriented labels for basket research without touching broker positions."""
    out = _normalize_df(df)
    if out.empty or "close" not in out.columns:
        return out
    try:
        out = add_indicators(out.copy())
    except Exception:
        pass
    out = _normalize_df(out)
    atr = pd.to_numeric(out.get("atr", 0), errors="coerce").replace(0, np.nan)
    future = out["close"].shift(-int(max(1, horizon)))
    move_atr = (future - out["close"]) / atr
    out["exit_buy_pressure_label"] = np.where(move_atr < -float(adverse_atr), "EXIT_BUY_RISK", np.where(move_atr > float(favorable_atr), "HOLD_BUY_OK", "WAIT"))
    out["exit_sell_pressure_label"] = np.where(move_atr > float(adverse_atr), "EXIT_SELL_RISK", np.where(move_atr < -float(favorable_atr), "HOLD_SELL_OK", "WAIT"))
    out["exit_label_horizon"] = int(max(1, horizon))
    out["exit_label_adverse_atr"] = float(adverse_atr)
    out["exit_label_favorable_atr"] = float(favorable_atr)
    return _add_train_regime_columns(out.replace([np.inf, -np.inf], np.nan).ffill().fillna(0))


def _render_cross_tab_relationship_panel(live_df, train_df):
    st.markdown("### 🧭 Cross-tab Data Relationship")
    st.caption("This verifies that Train Data is using the same shared dataframe as Home, Engine, Pre Original, and database autosave. It does not open another connector.")
    checks = []
    live_ok = isinstance(live_df, pd.DataFrame) and not live_df.empty
    train_ok = isinstance(train_df, pd.DataFrame) and not train_df.empty
    checks.append({"check": "Sidebar/shared live dataframe", "state": "OK" if live_ok else "EMPTY", "detail": f"rows={len(live_df) if isinstance(live_df, pd.DataFrame) else 0}"})
    checks.append({"check": "Training memory dataframe", "state": "OK" if train_ok else "EMPTY", "detail": f"rows={len(train_df) if isinstance(train_df, pd.DataFrame) else 0}"})
    for key in ["symbol", "timeframe", "source", "connected", "last_fetch", "data_version"]:
        val = st.session_state.get(key, "")
        checks.append({"check": f"session_state.{key}", "state": "SET" if val not in [None, ""] else "EMPTY", "detail": str(val)[:120]})
    st.dataframe(pd.DataFrame(checks), use_container_width=True, height=330)
    if live_ok and train_ok and "time" in live_df.columns and "time" in train_df.columns:
        c1, c2, c3 = st.columns(3)
        c1.metric("Live last candle", str(pd.to_datetime(live_df["time"]).max())[:19])
        c2.metric("Train last candle", str(pd.to_datetime(train_df["time"]).max())[:19])
        lag = pd.to_datetime(live_df["time"]).max() - pd.to_datetime(train_df["time"]).max()
        c3.metric("Train lag", str(lag))
    st.info("Best workflow: connect once in sidebar → open Home/Engine to refresh data → open Train Data → Collect/Auto collect → validate model.")


def _render_exit_label_panel(train_df):
    st.markdown("### 🚪 Exit Label Builder")
    st.caption("Creates research labels for when BUY-side or SELL-side baskets may become risky. This is only analytics data, not an order command.")
    if train_df is None or train_df.empty:
        st.info("No training data available yet.")
        return
    c1, c2, c3 = st.columns(3)
    horizon = c1.slider("Exit label horizon candles", 3, 240, int(st.session_state.get("train_exit_horizon", 24)), key="train_exit_horizon")
    adverse = c2.slider("Adverse move ATR", 0.05, 3.0, float(st.session_state.get("train_exit_adverse_atr", 0.35)), 0.05, key="train_exit_adverse_atr")
    favorable = c3.slider("Favorable hold ATR", 0.05, 3.0, float(st.session_state.get("train_exit_favorable_atr", 0.25)), 0.05, key="train_exit_favorable_atr")
    exit_df = _build_exit_training_labels(train_df, adverse_atr=adverse, favorable_atr=favorable, horizon=horizon)
    if exit_df.empty:
        st.warning("Could not build exit labels from current data.")
        return
    r1, r2 = st.columns(2)
    buy_rep = exit_df["exit_buy_pressure_label"].value_counts().rename_axis("label").reset_index(name="rows")
    sell_rep = exit_df["exit_sell_pressure_label"].value_counts().rename_axis("label").reset_index(name="rows")
    with r1:
        st.markdown("#### BUY-side exit pressure")
        st.dataframe(buy_rep, use_container_width=True, height=220)
    with r2:
        st.markdown("#### SELL-side exit pressure")
        st.dataframe(sell_rep, use_container_width=True, height=220)
    if st.button("💾 Save exit-label training memory", use_container_width=True):
        st.session_state.training_df = exit_df
        ok = save_market_cache(exit_df, name="training_data_cache", max_rows=int(st.session_state.get("train_max_memory_rows", 50000)))
        append_csv("training_snapshots", {"time": pd.Timestamp.now(), "reason": "exit_label_memory_save", "rows": len(exit_df), "horizon": horizon, "adverse_atr": adverse, "favorable_atr": favorable})
        st.success("Exit-label memory saved." if ok else "Exit labels created in session; cache save did not confirm.")
    with st.expander("Open exit-labeled rows", expanded=False):
        cols = [c for c in ["time", "session_bucket", "close", "adx", "pressure", "atr", "future_move_atr", "target_direction", "exit_buy_pressure_label", "exit_sell_pressure_label"] if c in exit_df.columns]
        st.dataframe(exit_df[cols].tail(1500) if cols else exit_df.tail(1500), use_container_width=True, height=380)


def _render_readiness_card(train_df):
    ready = _training_readiness_score(train_df)
    c1, c2 = st.columns([1, 3])
    c1.metric("Readiness", ready["status"])
    c1.metric("Score", f"{ready['score']}/100")
    with c2:
        st.markdown("**How to improve this training set**")
        for reason in ready["reasons"][:5]:
            st.write("• " + str(reason))

def show():
    render_page_shell(
        "Train Data",
        "Incremental learning center using the same sidebar/shared dataframe as Home and Engine.",
        "🧠",
    )
    st.markdown("# 🧠 Train Data Pro")
    st.caption("Incremental learning center. It reuses the global sidebar connector, protects the original code, and saves training memory safely for future decisions.")

    section = choice_buttons(
        "Open Train Data section",
        ["🧠 Live Training", "📊 Model Validation", "🚪 Exit Labels", "🧮 Math/ML Diagnostics", "📅 History Search", "🧪 Feature Health", "📈 Session Edge", "🧭 Cross Tab Link", "🗄️ Database Center"],
        key="train_main_section",
        columns=5,
        default="🧠 Live Training",
    )

    if section == "🗄️ Database Center":
        try:
            from tabs.database_tab import show as show_database
            show_database()
        except Exception as exc:
            st.error("Database Center could not load inside Train Data.")
            st.exception(exc)
        return

    df, cache_df, source_note = _source_frame()
    st.session_state.setdefault("training_df", cache_df if not cache_df.empty else pd.DataFrame())

    with st.expander("🔌 Shared data status", expanded=False):
        render_metric_cards([
            {"label": "Active source", "value": st.session_state.get("source", "DISCONNECTED")},
            {"label": "Symbol", "value": st.session_state.get("symbol", "XAUUSD")},
            {"label": "Timeframe", "value": st.session_state.get("timeframe", "M1")},
            {"label": "Live rows", "value": f"{len(df):,}"},
            {"label": "Using", "value": source_note},
        ])
        st.info("Train Data does not open a second API connection. It learns from the same shared dataframe used by Home and Engine, then falls back to saved cache when live data is empty.")

    cfg1, cfg2, cfg3, cfg4 = st.columns(4)
    with cfg1:
        horizon = st.slider("Label horizon candles", 3, 240, int(st.session_state.get("train_horizon", 12)), key="train_horizon")
    with cfg2:
        min_move_atr = st.slider("Min future move in ATR", 0.05, 2.00, float(st.session_state.get("train_min_move_atr", 0.15)), 0.05, key="train_min_move_atr")
    with cfg3:
        interval = st.slider("Refresh seconds", 5, 300, int(st.session_state.get("train_refresh_seconds", 10)), key="train_refresh_seconds")
    with cfg4:
        max_memory = st.slider("Max memory rows", 10000, 250000, int(st.session_state.get("train_max_memory_rows", 50000)), 5000, key="train_max_memory_rows")

    auto = st.checkbox("Auto collect latest shared data on refresh", value=True, key="train_auto_collect")
    if auto:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=interval * 1000, key="train_live_refresh")
        except Exception:
            pass
        if not df.empty:
            _collect_training_rows(df, "AUTO", horizon=horizon, min_move_atr=min_move_atr)

    train_df = _normalize_df(st.session_state.get("training_df"))
    if not train_df.empty and len(train_df) > max_memory:
        train_df = train_df.tail(max_memory).reset_index(drop=True)
        st.session_state.training_df = train_df
    train_df = _add_train_regime_columns(train_df)
    quality = _quality_report(df if not df.empty else train_df)

    render_metric_cards([
        {"label": "Connected rows", "value": f"{len(df):,}"},
        {"label": "Training rows", "value": f"{len(train_df):,}"},
        {"label": "Data quality", "value": quality["status"]},
        {"label": "Quality score", "value": f"{quality['score']}/100"},
        {"label": "Cache rows", "value": f"{len(cache_df):,}"},
        {"label": "Auto save", "value": "ON" if auto else "MANUAL"},
    ])

    with st.expander("🧪 Data quality details", expanded=False):
        for issue in quality["issues"]:
            st.write("• " + str(issue))

    with st.expander("🧰 Manual training controls", expanded=False):
        b1, b2, b3, b4, b5 = st.columns(5)
        if b1.button("➕ Collect now", use_container_width=True):
            n = _collect_training_rows(df, "MANUAL", horizon=horizon, min_move_atr=min_move_atr)
            st.success(f"Collected/prepared {n:,} rows.")
            _safe_rerun()
        if b2.button("📥 Reload cache", use_container_width=True):
            st.session_state.training_df = _load_training_cache()
            st.success("Reloaded saved training cache.")
            _safe_rerun()
        if b3.button("💾 Save now", use_container_width=True):
            ok = save_market_cache(train_df, name="training_data_cache", max_rows=max_memory) if not train_df.empty else False
            append_csv("training_snapshots", {"time": pd.Timestamp.now(), "reason": "manual_train_save", "rows": len(train_df), "horizon": horizon, "min_move_atr": min_move_atr})
            st.success("Saved training cache." if ok else "Nothing saved yet.")
        if b4.button("🧹 Clear memory", use_container_width=True):
            st.session_state.training_df = pd.DataFrame()
            st.session_state.training_rows = []
            _safe_rerun()
        if b5.button("🔁 Prepare from cache", use_container_width=True):
            base = cache_df if not cache_df.empty else df
            st.session_state.training_df = _prepare_training_frame(base, horizon=horizon, min_move_atr=min_move_atr)
            st.success("Prepared labels from available cache/live data.")
            _safe_rerun()

    _auto_save_training_result(train_df, df)
    st.caption("✅ Safe learning memory: cache + snapshots save automatically every 60 seconds when rows exist.")

    if train_df.empty:
        st.info("No training rows yet. Connect from the sidebar, press Collect now, or reload saved cache.")
        return

    _render_learning_memory(train_df)
    _render_readiness_card(train_df)

    if section == "🧭 Cross Tab Link":
        _render_cross_tab_relationship_panel(df, train_df)
        return

    if section == "🚪 Exit Labels":
        _render_exit_label_panel(train_df)
        return

    try:
        q = quant_stack(train_df.tail(3000), st.session_state.get("trade_history", []), st.session_state.get("account_snapshot", {}))
        m = st.columns(5)
        m[0].metric("Instant Bias", q.get("bias", "WAIT"))
        m[1].metric("Safety /10", q.get("scale10", 0))
        m[2].metric("Safety %", q.get("safe_pct", 0))
        m[3].metric("Regime", q.get("regime", "N/A"))
        m[4].metric("ML Conf %", q.get("ml_conf_pct", "N/A"))
    except Exception as exc:
        st.warning(f"Instant result unavailable: {exc}")


    if section == "🧮 Math/ML Diagnostics":
        st.markdown("### 🧮 Math / ML Algorithm Diagnostics")
        st.caption("This checks the upgraded shared quant core used by Home, Engine, Doo Prime, Account, Mix, and Train Data.")
        try:
            snap = trend_math_snapshot(train_df.tail(5000) if not train_df.empty else df)
            c = st.columns(6)
            c[0].metric("Status", snap.get("status", "N/A"))
            c[1].metric("Bias", snap.get("bias", "WAIT"))
            c[2].metric("Safe %", snap.get("safe_pct", 0))
            c[3].metric("Regime", snap.get("regime", "UNKNOWN"))
            c[4].metric("Efficiency %", snap.get("efficiency", 0))
            c[5].metric("Rows", snap.get("rows", 0))
            st.json(snap)
        except Exception as exc:
            st.warning(f"Diagnostics unavailable: {exc}")
        st.markdown("#### Algorithm quality checks")
        health = _feature_health_report(train_df)
        if health.empty:
            st.info("No prepared feature table yet. Collect data first.")
        else:
            st.dataframe(health, use_container_width=True, height=420)
            usable_pct = round(float(((health.get("usable") == "YES").mean()) * 100), 2) if "usable" in health.columns else 0
            st.metric("Usable feature %", usable_pct)
            st.caption("Good model quality requires enough rows, non-flat features, balanced labels, and walk-forward validation. Do not trust high accuracy if labels are one-sided.")
        return

    if section == "📅 History Search":
        _history_search_panel(train_df)
        return

    if section == "🧪 Feature Health":
        st.markdown("### 🧪 Feature Health")
        health = _feature_health_report(train_df)
        st.dataframe(health, use_container_width=True, height=420)
        bad = health[health.get("usable", "YES") == "CHECK"] if not health.empty else pd.DataFrame()
        if not bad.empty:
            st.warning("Some features are flat, sparse, or mostly zero. Check connector data and indicator generation before relying on validation.")
        return

    if section == "📈 Session Edge":
        st.markdown("### 📈 Session Edge")
        sess = _session_edge_report(train_df)
        if sess.empty:
            st.info("Need time and label data for session edge analysis.")
        else:
            st.dataframe(sess, use_container_width=True, height=300)
            st.bar_chart(sess.set_index("session_bucket")[["buy_pct", "sell_pct"]])
        return

    if section == "📊 Model Validation":
        st.markdown("### 📊 Walk-forward Model Validation")
        mode = choice_buttons("Validation mode", ["3-side BUY/SELL/WAIT", "BUY probability legacy"], key="train_validation_mode", columns=2, default="3-side BUY/SELL/WAIT")
        if mode == "3-side BUY/SELL/WAIT":
            result, msg = _train_multiclass_validation(train_df)
            if result is None:
                st.warning(msg)
            else:
                metrics, importances, conf = result
                c = st.columns(7)
                c[0].metric("Bias", metrics["bias"])
                c[1].metric("BUY %", metrics["buy_probability"])
                c[2].metric("SELL %", metrics["sell_probability"])
                c[3].metric("WAIT %", metrics["wait_probability"])
                c[4].metric("Gap %", metrics["confidence_gap"])
                c[5].metric("Accuracy %", metrics["accuracy"])
                c[6].metric("Test rows", metrics["test_rows"])
                st.caption("Walk-forward split only uses older rows to predict newer rows. This reduces look-ahead leakage and is safer for trading research.")
                st.bar_chart(importances.set_index("feature").head(12))
                with st.expander("Confusion matrix", expanded=False):
                    st.dataframe(conf, use_container_width=True)
                if st.button("💾 Save model snapshot", use_container_width=True):
                    st.success("Model snapshot saved." if _save_model_snapshot(metrics, importances) else "Snapshot save failed.")
        else:
            result, msg = _train_validation(train_df)
            if result is None:
                st.warning(msg)
            else:
                metrics, importances = result
                c = st.columns(6)
                c[0].metric("Bias", metrics["bias"])
                c[1].metric("BUY prob", metrics["last_buy_probability"])
                c[2].metric("SELL prob", metrics["last_sell_probability"])
                c[3].metric("Accuracy %", metrics["accuracy"])
                c[4].metric("Precision %", metrics["precision"])
                c[5].metric("Recall %", metrics["recall"])
                st.bar_chart(importances.set_index("feature").head(12))
        with st.expander("📋 Open prepared validation data", expanded=False):
            st.dataframe(train_df.tail(1500), use_container_width=True, height=360)
        return

    if "close" in train_df.columns and "time" in train_df.columns:
        st.line_chart(train_df.set_index("time")[["close"]].tail(1500))

    dist = _label_balance_report(train_df)
    if not dist.empty:
        with st.expander("🎯 Open label distribution", expanded=True):
            st.dataframe(dist, use_container_width=True)
            st.bar_chart(dist.set_index("label")[["rows"]])

    with st.expander("🧠 Open training feature table", expanded=False):
        cols = [c for c in ["time", "symbol", "timeframe", "session_bucket", "open", "high", "low", "close", "adx", "pressure", "atr", "directional_efficiency", "future_move_pct", "future_move_atr", "target_direction"] if c in train_df.columns]
        st.dataframe(train_df[cols].tail(1500) if cols else train_df.tail(1500), use_container_width=True, height=380)

    csv = train_df.tail(50000).to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Download latest training CSV", csv, file_name="training_data_cache_latest.csv", mime="text/csv", use_container_width=True)
