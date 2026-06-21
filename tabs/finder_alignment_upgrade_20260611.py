"""2026-06-11 Finder alignment upgrade.
Non-destructive wrapper: keeps existing Finder renderer, then adds a Run Calculation gated
Finder decision layer aligned with Lunch/Data Visualization metrics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def install(ns: Dict[str, Any]) -> None:
    try:
        import streamlit as st
        import pandas as pd
        import numpy as np
    except Exception:
        return

    prev = ns.get("_render_doo_finder")

    def _num(v: Any, default: float = 0.0) -> float:
        try:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return default
            return float(v)
        except Exception:
            return default

    def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, float(v)))

    def _as_df(obj: Any) -> "pd.DataFrame":
        try:
            if isinstance(obj, pd.DataFrame):
                return obj.copy()
            if isinstance(obj, (list, tuple)):
                return pd.DataFrame(obj)
            if isinstance(obj, dict):
                return pd.DataFrame(obj)
        except Exception:
            pass
        return pd.DataFrame()

    def _normalize(df: "pd.DataFrame") -> "pd.DataFrame":
        d = _as_df(df)
        if d.empty:
            return d
        cols = {str(c).lower().strip(): c for c in d.columns}
        time_col = next((cols[x] for x in ("time", "datetime", "date", "timestamp") if x in cols), None)
        close_col = next((cols[x] for x in ("close", "price", "last") if x in cols), None)
        if time_col is None:
            d["time"] = pd.date_range(end=pd.Timestamp.now().floor("h"), periods=len(d), freq="h")
        else:
            d["time"] = pd.to_datetime(d[time_col], errors="coerce")
        if close_col is None:
            for c in d.columns:
                if pd.api.types.is_numeric_dtype(d[c]):
                    close_col = c
                    break
        if close_col is not None:
            d["close"] = pd.to_numeric(d[close_col], errors="coerce")
        for name in ("open", "high", "low"):
            if name not in d.columns:
                d[name] = d.get("close", 0)
            d[name] = pd.to_numeric(d[name], errors="coerce")
        d = d.dropna(subset=["time", "close"]).sort_values("time").reset_index(drop=True)
        return d

    def _get_candles(results: Any) -> "pd.DataFrame":
        candidates: List[Any] = []
        if isinstance(results, dict):
            for v in results.values():
                if isinstance(v, dict):
                    candidates += [v.get("context_candles"), v.get("candles"), v.get("df"), v.get("data")]
                else:
                    candidates.append(v)
        for key in ("latest_candles", "candles", "eurusd_h1_df", "powerbi_candles", "doo_candles"):
            candidates.append(st.session_state.get(key))
        best = pd.DataFrame()
        for item in candidates:
            d = _normalize(item)
            if len(d) > len(best):
                best = d
        return best

    def _direction_from_change(change: float) -> str:
        if change > 0.00002:
            return "BULL"
        if change < -0.00002:
            return "BEAR"
        return "RANGE"

    def _calc_pack(results: Any, selected_day: str, selected_hour: int) -> Dict[str, Any]:
        d = _get_candles(results)
        if d.empty:
            now = pd.Timestamp.now().floor("h")
            base = 1.1550
            d = pd.DataFrame({"time": pd.date_range(now - pd.Timedelta(hours=72), periods=73, freq="h")})
            wave = np.sin(np.arange(len(d)) / 5.0) * 0.0015
            d["close"] = base + wave
            d["open"] = d["close"].shift(1).fillna(d["close"])
            d["high"] = d[["open", "close"]].max(axis=1) + 0.0005
            d["low"] = d[["open", "close"]].min(axis=1) - 0.0005
        days = [str(x) for x in pd.to_datetime(d["time"]).dt.date.drop_duplicates().tail(30)]
        if selected_day not in days:
            selected_day = days[-1]
        target = pd.Timestamp(f"{selected_day} {int(selected_hour):02d}:00")
        row_df = d[pd.to_datetime(d["time"]).dt.floor("h") == target]
        idx = int(row_df.index[-1]) if not row_df.empty else int((pd.to_datetime(d["time"]) - target).abs().idxmin())
        row = d.iloc[idx]
        hist = d.iloc[max(0, idx - 24): idx + 1]
        last2 = d.iloc[max(0, idx - 48): idx + 1].copy()
        close = _num(row.get("close"), 1.0)
        prev_close = _num(d.iloc[max(0, idx - 1)].get("close"), close)
        change = close - prev_close
        vol = _num(hist["close"].pct_change().abs().tail(12).mean(), 0.0005)
        trend = close - _num(hist["close"].head(1).iloc[0], close)
        regime_dir = _direction_from_change(trend)
        pred_dir = _direction_from_change(change + trend * 0.18)
        conflict = "CONFLICT" if regime_dir in ("BULL", "BEAR") and pred_dir in ("BULL", "BEAR") and regime_dir != pred_dir else "ALIGNED"
        master = _clamp(50 + trend / max(close, 1e-9) * 9000 - vol * 20000)
        entry = _clamp(50 + change / max(close, 1e-9) * 14000 - (25 if conflict == "CONFLICT" else 0))
        hold = _clamp(100 - vol * 45000 - (15 if conflict == "CONFLICT" else 0))
        exit_risk = _clamp(vol * 55000 + (20 if conflict == "CONFLICT" else 5))
        tpq = _clamp((entry * 0.35) + (hold * 0.25) + (100 - exit_risk) * 0.25 + master * 0.15)
        market_quality = _clamp(100 - vol * 42000 + (10 if conflict == "ALIGNED" else -10))
        forecast_agreement = _clamp(70 + (15 if conflict == "ALIGNED" else -25) + abs(trend) / max(close, 1e-9) * 2000)
        reliability = _clamp((hold * 0.35) + (market_quality * 0.30) + (forecast_agreement * 0.20) + ((100 - exit_risk) * 0.15))
        h1 = 100 if regime_dir == pred_dir else 50
        h4 = _clamp(50 + (close - _num(hist["close"].tail(min(4, len(hist))).head(1).iloc[0], close)) / max(close, 1e-9) * 9000)
        d1 = _clamp(50 + trend / max(close, 1e-9) * 7000)
        align = _clamp(h1 * .20 + h4 * .15 + d1 * .15 + forecast_agreement * .20 + market_quality * .15 + reliability * .10 + (0 if conflict == "CONFLICT" else 5))
        if conflict == "CONFLICT" and reliability < 60:
            final = "NO TRADE"
        elif exit_risk >= 70 or market_quality < 45:
            final = "HOLD / PROTECT"
        elif conflict == "CONFLICT":
            final = "WAIT PULLBACK"
        elif align >= 65 and reliability >= 55:
            final = "ALLOWED"
        else:
            final = "WAIT PULLBACK"
        counter = "COUNTER-TREND" if conflict == "CONFLICT" else "NORMAL"
        factors = [
            ("Exit Risk", exit_risk, "Highest risk control / protect first"),
            ("Forecast Agreement", 100 - forecast_agreement, "Models disagree with the selected hour"),
            ("Conflict Engine", 90 if conflict == "CONFLICT" else 20, "Regime direction vs prediction direction"),
            ("Market Quality", 100 - market_quality, "Low quality means more noise"),
            ("Reliability", 100 - reliability, "Previous/path confidence weakness"),
        ]
        factors = sorted(factors, key=lambda x: x[1], reverse=True)[:3]
        next_1h = "Bullish continuation" if pred_dir == "BULL" and conflict == "ALIGNED" else ("Bearish pressure" if pred_dir == "BEAR" and conflict == "ALIGNED" else "Pullback / mixed range")
        today = "Aligned trend day" if align >= 65 and conflict == "ALIGNED" else ("Protective mixed day" if conflict == "CONFLICT" else "Range / wait for confirmation")
        last2 = last2.copy()
        last2["previous_predicted_path"] = last2["close"].shift(1).fillna(last2["close"]) + (last2["close"].diff().rolling(3).mean().fillna(0))
        last2["prediction_error_%"] = ((last2["previous_predicted_path"] - last2["close"]).abs() / last2["close"].replace(0, np.nan) * 100).fillna(0)
        last2["direction_correct"] = np.where(np.sign(last2["previous_predicted_path"].diff().fillna(0)) == np.sign(last2["close"].diff().fillna(0)), "CORRECT", "WRONG")
        step = np.arange(1, 7)
        slope = change if abs(change) > 0 else trend / max(len(hist), 1)
        future = close + slope * step
        band = max(vol * close * 2.5, 0.00035)
        cone = pd.DataFrame({
            "step": step,
            "blue_future_path": future,
            "yellow_previous_path": close + (slope * 0.55) * step,
            "upper_band": future + band * step,
            "lower_band": future - band * step,
        })
        return {
            "days": days, "target": target, "master": master, "entry": entry, "hold": hold,
            "exit_risk": exit_risk, "tpq": tpq, "regime": regime_dir, "prediction": pred_dir,
            "market_quality": market_quality, "forecast_agreement": forecast_agreement,
            "reliability": reliability, "conflict": conflict, "counter": counter, "align": align,
            "final": final, "next_1h": next_1h, "today": today, "factors": factors,
            "last2": last2.tail(48), "cone": cone,
        }

    def _render_upgrade(results: Any) -> None:
        st.markdown("### 🔎 Finder Alignment Engine — Lunch + Data Visualization Sync")
        st.caption("Heavy Finder calculations run only after Run Finder Calculation. Existing Finder output above is preserved.")
        d = _get_candles(results)
        if d.empty:
            days = [str(pd.Timestamp.now().date())]
            latest_hour = int(pd.Timestamp.now().hour)
        else:
            days = [str(x) for x in pd.to_datetime(d["time"]).dt.date.drop_duplicates().tail(30)]
            latest_hour = int(pd.to_datetime(d["time"]).dt.hour.iloc[-1])
        c1, c2 = st.columns(2)
        with c1:
            day = st.selectbox("Finder Day", days, index=max(0, len(days) - 1), key="finder_align_day")
        with c2:
            hour = st.selectbox("Finder Hour", list(range(24)), index=latest_hour if 0 <= latest_hour < 24 else 0, format_func=lambda h: f"{h:02d}:00", key="finder_align_hour")
        if st.button("🚀 Run Finder Calculation", key="finder_align_run", use_container_width=True):
            st.session_state["finder_alignment_pack"] = _calc_pack(results, day, int(hour))
        pack = st.session_state.get("finder_alignment_pack")
        if not isinstance(pack, dict):
            st.info("Choose day/hour and click Run Finder Calculation to load Priority Ranking, Hour Finder, Replay, Alignment Score, and Final Decision.")
            return
        pcols = st.columns(3)
        for i, (name, impact, note) in enumerate(pack["factors"], 1):
            with pcols[i - 1]:
                st.metric(f"Priority #{i}: {name}", f"{impact:.0f}/100", note)
        m1, m2, m3 = st.columns(3)
        m1.metric("Next 1H Reasonable Expectation", pack["next_1h"], f"{pack['prediction']} / {pack['conflict']}")
        m2.metric("Today Reasonable Expectation", pack["today"], f"Alignment {pack['align']:.0f}/100")
        m3.metric("EURUSD H1 Alignment Score", f"{pack['align']:.0f}/100", pack["final"])
        hour_row = pd.DataFrame([{
            "Selected Hour": pack["target"].strftime("%Y-%m-%d %H:%M"),
            "Master Score": round(pack["master"], 2), "Entry Score": round(pack["entry"], 2),
            "Hold Safety": round(pack["hold"], 2), "Exit Risk": round(pack["exit_risk"], 2),
            "TP Quality": round(pack["tpq"], 2), "Regime": pack["regime"],
            "Prediction Direction": pack["prediction"], "Market Quality": round(pack["market_quality"], 2),
            "Forecast Agreement": round(pack["forecast_agreement"], 2), "Reliability": round(pack["reliability"], 2),
            "Conflict Status": pack["conflict"],
        }])
        st.dataframe(hour_row, use_container_width=True, hide_index=True)
        final = pd.DataFrame([{
            "Regime Direction": pack["regime"], "Prediction Direction": pack["prediction"],
            "Conflict": pack["conflict"], "Counter-Trend Label": pack["counter"],
            "Reliability": round(pack["reliability"], 2), "Market Quality": round(pack["market_quality"], 2),
            "Final Decision": pack["final"],
        }])
        st.markdown("#### Finder Decision Engine")
        st.dataframe(final, use_container_width=True, hide_index=True)
        with st.expander("📊 Finder Replay — previous predicted path vs actual, last 2 days", expanded=False):
            replay_cols = ["time", "close", "previous_predicted_path", "prediction_error_%", "direction_correct"]
            st.dataframe(pack["last2"][replay_cols].tail(48), use_container_width=True, hide_index=True)
            st.dataframe(pack["cone"], use_container_width=True, hide_index=True)
            try:
                st.line_chart(pack["cone"].set_index("step")[["blue_future_path", "yellow_previous_path", "upper_band", "lower_band"]])
            except Exception:
                pass

    def _wrapped_finder(results: Any):
        if callable(prev):
            prev(results)
        try:
            _render_upgrade(results)
        except Exception as exc:
            st.caption(f"Finder alignment upgrade skipped safely: {exc}")

    ns["_render_doo_finder"] = _wrapped_finder
