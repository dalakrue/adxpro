"""Causal deterministic calibration for the existing PowerBI projection paths.

This module does not train a model and does not replace raw red/yellow/blue
outputs.  It calibrates each existing path and horizon from completed historical
prediction outcomes only, creates bounded reliability weights, and derives
residual-quantile bands.  Every market feature is trailing/causal.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence
import math
import numpy as np
import pandas as pd

CALIBRATION_VERSION = "powerbi-path-calibration-20260618-v2"
PATHS = ("red", "yellow", "blue")


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else float(default)
    except Exception:
        return float(default)


def _clip(value: Any, low: float, high: float) -> float:
    return float(max(low, min(high, _finite(value, low))))


def _find_col(frame: pd.DataFrame, aliases: Iterable[str]) -> Optional[str]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    norm = {str(c).strip().lower().replace("_", " "): c for c in frame.columns}
    for alias in aliases:
        key = str(alias).strip().lower().replace("_", " ")
        if key in norm:
            return norm[key]
    for alias in aliases:
        key = str(alias).strip().lower().replace("_", " ")
        for n, c in norm.items():
            if key and key in n:
                return c
    return None


def _prepare_market(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame) or data.empty:
        return pd.DataFrame()
    t = _find_col(data, ("time", "datetime", "timestamp", "date")); c = _find_col(data, ("close", "c"))
    if t is None or c is None:
        return pd.DataFrame()
    o = _find_col(data, ("open", "o")); h = _find_col(data, ("high", "h")); l = _find_col(data, ("low", "l"))
    out = pd.DataFrame({"time": pd.to_datetime(data[t], errors="coerce"), "close": pd.to_numeric(data[c], errors="coerce")})
    out["open"] = pd.to_numeric(data[o], errors="coerce") if o else out["close"]
    out["high"] = pd.to_numeric(data[h], errors="coerce") if h else out[["open", "close"]].max(axis=1)
    out["low"] = pd.to_numeric(data[l], errors="coerce") if l else out[["open", "close"]].min(axis=1)
    out = out.dropna(subset=["time", "close"]).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    if out.empty:
        return out
    out["high"] = out[["open", "high", "close"]].max(axis=1)
    out["low"] = out[["open", "low", "close"]].min(axis=1)
    return out


def _bar_delta(market: pd.DataFrame) -> pd.Timedelta:
    d = pd.to_datetime(market["time"], errors="coerce").diff().dropna()
    median = d.median() if len(d) else pd.Timedelta(hours=1)
    return median if pd.notna(median) and median.total_seconds() > 0 else pd.Timedelta(hours=1)


def _atr(market: pd.DataFrame) -> float:
    prev = market["close"].shift(1)
    tr = pd.concat([(market["high"]-market["low"]).abs(), (market["high"]-prev).abs(), (market["low"]-prev).abs()], axis=1).max(axis=1)
    value = _finite(tr.tail(96).median(), 0.0)
    return value if value > 0 else max(abs(_finite(market["close"].iloc[-1])) * .00035, 1e-8)


def _source_path(source: pd.DataFrame, *, path: str, horizon: int, future_times: Sequence[pd.Timestamp], anchor: float) -> pd.DataFrame:
    columns = ["step", "time", f"{path}_raw"]
    if not isinstance(source, pd.DataFrame) or source.empty:
        return pd.DataFrame(columns=columns)
    value_col = _find_col(source, (f"{path} path", "path", "accuracy adjusted price", "predicted close", "pred close", "projected close", "yellow predicted close", "calibrated close", "forecast close", "close", "projected path"))
    if value_col is None:
        return pd.DataFrame(columns=columns)
    time_col = _find_col(source, ("time", "future time", "datetime", "date", "projection time"))
    step_col = _find_col(source, ("step", "prediction step", "horizon", "horizon point", "projection step"))
    work = pd.DataFrame({f"{path}_raw": pd.to_numeric(source[value_col], errors="coerce")})
    work["step"] = pd.to_numeric(source[step_col], errors="coerce") if step_col else np.arange(1, len(work)+1)
    work = work.dropna(subset=[f"{path}_raw", "step"])
    work["step"] = work["step"].astype(int)
    work = work[(work["step"] >= 1) & (work["step"] <= horizon)].sort_values("step").drop_duplicates("step", keep="last").head(horizon).copy()
    if work.empty:
        return pd.DataFrame(columns=columns)
    if time_col:
        mapped = pd.to_datetime(source.loc[work.index, time_col], errors="coerce")
        work["time"] = mapped.to_numpy()
    else:
        work["time"] = [future_times[min(max(int(x)-1, 0), len(future_times)-1)] for x in work["step"]]
    anchor_col = _find_col(source, ("anchor price", "anchor_price", "start price", "predicted open", "origin close", "open"))
    if anchor_col is not None:
        source_anchor = _finite(source[anchor_col].dropna().iloc[0] if source[anchor_col].notna().any() else anchor, anchor)
        work[f"{path}_raw"] = anchor + (work[f"{path}_raw"] - source_anchor)
    return work[columns].reset_index(drop=True)


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    if len(values) == 0:
        return 0.0
    order = np.argsort(values)
    v = values[order]; w = weights[order]
    total = float(w.sum())
    if total <= 0:
        return float(np.median(v))
    return float(v[np.searchsorted(np.cumsum(w), total * .5, side="left")])


def _winsorized(values: pd.Series) -> np.ndarray:
    arr = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    if len(arr) < 4:
        return arr
    med = float(np.median(arr)); mad = float(np.median(np.abs(arr-med)))
    if mad > 1e-12:
        lo, hi = med - 5.0 * 1.4826 * mad, med + 5.0 * 1.4826 * mad
    else:
        lo, hi = np.quantile(arr, [.05, .95])
    return np.clip(arr, lo, hi)


def _residual_history(history: pd.DataFrame, anchor_time: pd.Timestamp) -> pd.DataFrame:
    columns = ["path", "horizon", "residual", "abs_error", "completed_time", "regime", "direction_correct"]
    if not isinstance(history, pd.DataFrame) or history.empty:
        return pd.DataFrame(columns=columns)
    actual_col = _find_col(history, ("actual close", "actual", "close actual", "real close"))
    pred_col = _find_col(history, ("predicted close", "pred close", "prediction", "projected close", "forecast close"))
    if actual_col is None or pred_col is None:
        return pd.DataFrame(columns=columns)
    actual = pd.to_numeric(history[actual_col], errors="coerce"); pred = pd.to_numeric(history[pred_col], errors="coerce")
    out = pd.DataFrame({"residual": actual-pred})
    out["abs_error"] = out["residual"].abs()
    pcol = _find_col(history, ("path", "model", "source path", "prediction path", "color"))
    hcol = _find_col(history, ("horizon", "step", "prediction step", "horizon point"))
    tcol = _find_col(history, ("target time", "actual time", "completed time", "time", "datetime", "timestamp"))
    rcol = _find_col(history, ("regime", "current regime", "major regime", "regime group"))
    dcol = _find_col(history, ("direction correct", "correct direction", "direction hit"))
    out["path"] = history[pcol].astype(str).str.lower() if pcol else "generic"
    out["path"] = out["path"].map(lambda x: next((p for p in PATHS if p in x), "generic"))
    out["horizon"] = pd.to_numeric(history[hcol], errors="coerce").fillna(0).astype(int) if hcol else 0
    out["completed_time"] = pd.to_datetime(history[tcol], errors="coerce") if tcol else pd.NaT
    out["regime"] = history[rcol].astype(str) if rcol else "GLOBAL"
    if dcol:
        values = history[dcol]
        if values.dtype == bool:
            out["direction_correct"] = values.astype(float)
        else:
            out["direction_correct"] = values.astype(str).str.upper().map({"TRUE":1.,"YES":1.,"CORRECT":1.,"1":1.,"FALSE":0.,"NO":0.,"WRONG":0.,"0":0.})
    else:
        out["direction_correct"] = np.nan
    out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=["residual"])
    if out["completed_time"].notna().any():
        out = out[(out["completed_time"].isna()) | (out["completed_time"] <= anchor_time)]
        out = out.sort_values("completed_time", na_position="first")
    return out.reset_index(drop=True)


def _subset_residuals(residuals: pd.DataFrame, path: str, horizon: int, regime: str | None = None) -> pd.DataFrame:
    if residuals.empty:
        return residuals
    p = residuals[(residuals["path"].isin([path, "generic"])) & (residuals["horizon"].isin([horizon, 0]))]
    if regime:
        same = p[p["regime"].astype(str).str.upper() == str(regime).upper()]
        return same
    return p


def _decay_weights(n: int, half_life: float = 45.0) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=float)
    age = np.arange(n-1, -1, -1, dtype=float)
    return np.exp(-math.log(2.0) * age / max(half_life, 1.0))


def _bias_for(residuals: pd.DataFrame, path: str, horizon: int, regime: str, atr: float) -> tuple[float, float, float, int, int, np.ndarray]:
    global_rows = _subset_residuals(residuals, path, horizon)
    same_rows = _subset_residuals(residuals, path, horizon, regime=regime) if regime else global_rows.iloc[0:0]
    global_values = _winsorized(global_rows["residual"])
    same_values = _winsorized(same_rows["residual"])
    global_bias = _weighted_median(global_values, _decay_weights(len(global_values))) if len(global_values) else 0.0
    same_bias = _weighted_median(same_values, _decay_weights(len(same_values), 30.0)) if len(same_values) else global_bias
    regime_weight = len(same_values) / (len(same_values) + 12.0) if len(same_values) else 0.0
    correction = regime_weight * same_bias + (1.0-regime_weight) * global_bias
    cap = max(atr * (1.5 + .35*math.sqrt(horizon)), 1e-9)
    correction = _clip(correction, -cap, cap)
    return correction, global_bias, same_bias, len(global_values), len(same_values), global_values


def _path_reliability(residuals: pd.DataFrame, path: str, horizon: int, atr: float, summary_direction: float | None) -> Dict[str, float]:
    rows = _subset_residuals(residuals, path, horizon)
    values = _winsorized(rows["residual"])
    n = len(values)
    if n:
        weights = _decay_weights(n)
        abs_med = _weighted_median(np.abs(values), weights)
        stability = float(np.median(np.abs(np.abs(values)-np.median(np.abs(values))))) if n >= 3 else abs_med
    else:
        abs_med = atr * .75; stability = atr * .5
    direct = rows["direction_correct"].dropna()
    direction = float(direct.tail(120).mean()*100.0) if len(direct) else (summary_direction if summary_direction is not None else 50.0)
    error_component = 1.0 / max(abs_med, atr*.20, 1e-10)
    stability_penalty = 1.0 / (1.0 + stability/max(atr, 1e-10))
    direction_factor = .65 + _clip(direction, 0, 100)/100.0*.70
    sample_factor = .50 + min(n/60.0, 1.0)*.50
    return {"raw_score": error_component*stability_penalty*direction_factor*sample_factor, "abs_error": abs_med, "stability": stability, "direction_accuracy": direction, "samples": float(n)}


def _bounded_weights(scores: Dict[str, float], available: list[str]) -> Dict[str, float]:
    if not available:
        return {}
    if len(available) == 1:
        return {available[0]: 1.0}
    vals = np.array([max(_finite(scores.get(p), 0.0), 1e-12) for p in available], dtype=float)
    vals /= vals.sum()
    lower, upper = .15, .55
    # Iterative bounded simplex projection; deterministic for identical inputs.
    w = vals.copy()
    for _ in range(12):
        w = np.clip(w, lower, upper)
        diff = 1.0 - float(w.sum())
        if abs(diff) < 1e-12:
            break
        if diff > 0:
            free = np.where(w < upper-1e-12)[0]
            if not len(free): break
            room = upper-w[free]; add = diff*room/room.sum(); w[free] += add
        else:
            free = np.where(w > lower+1e-12)[0]
            if not len(free): break
            room = w[free]-lower; take = (-diff)*room/room.sum(); w[free] -= take
    w /= w.sum()
    return {p: float(v) for p, v in zip(available, w)}


def _market_prior(market: pd.DataFrame, horizon: int, atr: float) -> list[float]:
    close = market["close"].astype(float); returns = close.pct_change().dropna()
    anchor = float(close.iloc[-1])
    drift = _finite(returns.tail(12).median(), 0.0)*.55 + _finite(returns.tail(48).median(), 0.0)*.25
    drift = _clip(drift, -atr/max(abs(anchor),1e-12), atr/max(abs(anchor),1e-12))
    values=[]; prev=anchor
    for step in range(1,horizon+1):
        target = prev*(1.0+drift*(.92**(step-1)))
        target = prev + _clip(target-prev, -atr*1.2, atr*1.2)
        values.append(max(target, 1e-9)); prev=values[-1]
    return values


def calibrate_projection_bundle(
    market_data: pd.DataFrame, *, red: pd.DataFrame|None=None, yellow: pd.DataFrame|None=None, blue: pd.DataFrame|None=None,
    horizon: int=6, bt_history: pd.DataFrame|None=None, bt_summary: Dict[str,Any]|None=None,
    regime_reliability: float|None=None, current_regime: str|None=None, transition_or_conflict: Any=None,
    calculation_timestamp: Any=None, source_data_timestamp: Any=None,
) -> Dict[str, Any]:
    market = _prepare_market(market_data)
    if market.empty or len(market) < 8:
        return {"ok":False,"message":"Need clean timestamped OHLC data."}
    horizon = int(max(1,min(int(horizon or 6),96)))
    anchor = float(market["close"].iloc[-1]); anchor_time = pd.Timestamp(market["time"].iloc[-1]); delta = _bar_delta(market); atr = _atr(market)
    future_times = [anchor_time+delta*step for step in range(1,horizon+1)]
    base = pd.DataFrame({"step":np.arange(1,horizon+1),"time":future_times})
    source_map={"red":red,"yellow":yellow,"blue":blue}
    for path in PATHS:
        frame=_source_path(source_map[path] if isinstance(source_map[path],pd.DataFrame) else pd.DataFrame(), path=path, horizon=horizon, future_times=future_times, anchor=anchor)
        if not frame.empty:
            base=base.merge(frame.drop(columns="time",errors="ignore"),on="step",how="left")
        else:
            base[f"{path}_raw"]=np.nan
    available=[p for p in PATHS if base[f"{p}_raw"].notna().any()]
    residuals=_residual_history(bt_history if isinstance(bt_history,pd.DataFrame) else pd.DataFrame(),anchor_time)
    summary=bt_summary if isinstance(bt_summary,dict) else {}
    direction_summary=None
    for k in ("direction_accuracy_pct","direction accuracy pct","direction_accuracy","accuracy_pct"):
        if k in summary:
            direction_summary=_finite(summary[k],50.0); direction_summary*=100 if 0<=direction_summary<=1 else 1; break
    regime=str(current_regime or "GLOBAL")
    regime_rel=_clip(regime_reliability if regime_reliability is not None else 55.0, 0, 100)
    expansion=any(x in regime.upper() for x in ("EXPANSION","VOLATILE"))
    recent_tr=(market["high"]-market["low"]).abs()
    if len(recent_tr)>=48 and _finite(recent_tr.tail(12).median(),0)>_finite(recent_tr.tail(48).median(),1)*1.35:
        expansion=True
    step_cap=atr*(2.0 if expansion else 1.5)
    corrections={p:[] for p in PATHS}; global_corr={p:[] for p in PATHS}; regime_corr={p:[] for p in PATHS}; sample_counts={p:[] for p in PATHS}; residual_samples={}
    for path in PATHS:
        calibrated=[]; prev=anchor
        for h in range(1,horizon+1):
            corr,g,same,ng,nr,vals=_bias_for(residuals,path,h,regime,atr)
            corrections[path].append(corr); global_corr[path].append(g); regime_corr[path].append(same); sample_counts[path].append((ng,nr)); residual_samples[f"{path}_H+{h}"]=vals.tolist()
            raw=_finite(base.loc[h-1,f"{path}_raw"],float("nan"))
            if math.isfinite(raw):
                target=raw+corr
                target=prev+_clip(target-prev,-step_cap,step_cap)
                target=max(target,1e-9); calibrated.append(target); prev=target
            else:
                calibrated.append(np.nan)
        base[f"{path}_path"]=calibrated
    priors=_market_prior(market,horizon,atr)
    main=[]; spreads=[]; weights_rows=[]; reliability_rows=[]; prev=anchor
    for h in range(1,horizon+1):
        vals={p:_finite(base.loc[h-1,f"{p}_path"],float("nan")) for p in available}
        vals={p:v for p,v in vals.items() if math.isfinite(v)}
        active=list(vals)
        if active:
            rels={p:_path_reliability(residuals,p,h,atr,direction_summary) for p in active}
            spread=float(np.median(np.abs(np.array(list(vals.values()))-np.median(list(vals.values()))))) if len(vals)>1 else 0.0
            raw_scores={p:rels[p]["raw_score"] for p in active}
            if len(active)>1 and spread>atr*.75:
                least=min(active,key=lambda p: raw_scores[p]); raw_scores[least]*=.60
            weights=_bounded_weights(raw_scores,active)
            consensus=sum(vals[p]*weights[p] for p in active)
            disagreement_ratio=_clip(spread/max(atr,1e-12),0,3)
            shrink=1.0/(1.0+.22*disagreement_ratio)
            target=prev+(consensus-prev)*shrink
            target=prev+_clip(target-prev,-step_cap,step_cap)
            rel_score=np.mean([_clip(100*(.45*min(rels[p]["samples"]/60,1)+.35*max(0,1-rels[p]["abs_error"]/(atr*2.5))+.20*rels[p]["direction_accuracy"]/100),0,100) for p in active])
        else:
            # Required safe fallback: flat from the latest completed close.
            spread=0.0; weights={}; target=anchor; rel_score=35.0
        target=max(_finite(target,anchor),1e-9); main.append(target); spreads.append(spread); prev=target
        weights_rows.append({"step":h,**{p:weights.get(p,0.0) for p in PATHS}})
        reliability_rows.append(rel_score)
    base["main_path"]=main; base["source_spread"]=spreads
    # Signed residual-quantile bands with causal regime/global histories.
    widths=[]; lowers=[]; uppers=[]; quantile_rows=[]; previous_width=0.0
    previous_lower_extent=0.0; previous_upper_extent=0.0
    conflict_text=str(transition_or_conflict or "").upper(); conflict_factor=1.20 if any(x in conflict_text for x in ("HIGH","CONFLICT","TRANSITION","TRUE")) else 1.0
    fallback_multiplier=1.35 if len(available)==1 else 1.65 if not available else 1.0
    for h in range(1,horizon+1):
        pooled=[]
        for p in available or PATHS:
            pooled.extend(residual_samples.get(f"{p}_H+{h}",[]))
        arr=np.asarray(pooled,dtype=float)
        if len(arr):
            q10=float(np.quantile(arr,.10)); q90=float(np.quantile(arr,.90)); empirical=max(float(np.median(np.abs(arr))),atr*.30)
        else:
            q10=-atr*(.45+.18*math.sqrt(h)); q90=atr*(.45+.18*math.sqrt(h)); empirical=atr*.55
        q10=min(q10,-empirical*.55); q90=max(q90,empirical*.55)
        rel=_clip(reliability_rows[h-1],0,100); disagreement=spreads[h-1]
        scale=(1.0+(100-rel)/100*.45)*(1.0+(100-regime_rel)/100*.25)*conflict_factor*fallback_multiplier
        volatility_floor=atr*(.42+.20*math.sqrt(h))
        lower_extent=(max(abs(min(q10,0.0)),volatility_floor)+disagreement*.85)*scale
        upper_extent=(max(max(q90,0.0),volatility_floor)+disagreement*.85)*scale
        lower_extent=max(lower_extent,previous_lower_extent*1.01 if previous_lower_extent else lower_extent)
        upper_extent=max(upper_extent,previous_upper_extent*1.01 if previous_upper_extent else upper_extent)
        previous_lower_extent=lower_extent; previous_upper_extent=upper_extent
        width=max(lower_extent,upper_extent,previous_width*1.01 if previous_width else 0.0); previous_width=width
        lo=max(main[h-1]-lower_extent,1e-9); hi=max(main[h-1]+upper_extent,main[h-1]); lowers.append(lo); uppers.append(hi); widths.append(width)
        quantile_rows.append({"step":h,"q10":q10,"q90":q90,"samples":len(arr),"lower_extent":lower_extent,"upper_extent":upper_extent})
    base["band_width"]=widths; base["lower_band"]=np.minimum(lowers,base["main_path"]); base["upper_band"]=np.maximum(uppers,base["main_path"])
    # All finite safety net.
    for col in ("main_path","lower_band","upper_band","band_width","source_spread"):
        base[col]=pd.to_numeric(base[col],errors="coerce").replace([np.inf,-np.inf],np.nan)
    base["main_path"]=base["main_path"].fillna(anchor).clip(lower=1e-9)
    base["band_width"]=base["band_width"].fillna(atr).clip(lower=0)
    base["lower_band"]=base["lower_band"].fillna(base["main_path"]-base["band_width"]).clip(lower=1e-9)
    base["upper_band"]=base["upper_band"].fillna(base["main_path"]+base["band_width"])
    base["lower_band"]=np.minimum(base["lower_band"],base["main_path"]); base["upper_band"]=np.maximum(base["upper_band"],base["main_path"])
    weights_df=pd.DataFrame(weights_rows)
    path_rel=float(np.mean(reliability_rows)) if reliability_rows else 35
    mean_rel=_clip(path_rel*.85+regime_rel*.15,25,92)
    if residuals.empty: mean_rel=min(mean_rel,58)
    agreement=_clip(100-float(np.mean(spreads))/max(atr,1e-12)*35,0,100)
    source_names=available if available else ["market_prior"]
    summary_out={
        "version":CALIBRATION_VERSION,"reliability_pct":round(mean_rel,2),"path_agreement_pct":round(agreement,2),
        "estimated_band_coverage_pct":round(_clip(72+min(len(residuals),80)*.18-(100-mean_rel)*.12,50,94),2),
        "median_abs_error_pct":round((_finite(residuals["abs_error"].median(),atr*.55)/max(abs(anchor),1e-12))*100,6),
        "error_samples":int(len(residuals)),"error_is_proxy":bool(residuals.empty),"direction_accuracy_pct":None if direction_summary is None else round(direction_summary,2),
        "atr_price":round(atr,8),"sources_used":source_names,"anchor_time":str(anchor_time),"anchor_price":round(anchor,8),
        "fallback_state":"ALL_PATHS_MISSING" if not available else "ONE_PATH_ONLY" if len(available)==1 else "PARTIAL_PATHS" if len(available)==2 else "NONE",
        "current_regime":regime,"regime_reliability_pct":round(regime_rel,2),"calculation_timestamp":str(calculation_timestamp or pd.Timestamp.utcnow()),"source_data_timestamp":str(source_data_timestamp or anchor_time),
    }
    main_df=base[["step","time","main_path","upper_band","lower_band","band_width","source_spread"]].copy()
    outputs={p:base[["step","time",f"{p}_path"]].dropna(subset=[f"{p}_path"]).copy() for p in PATHS}
    raw_frames={p:base[["step","time",f"{p}_raw"]].copy() for p in PATHS}
    audit={
        "raw_paths":raw_frames,"calibrated_paths":outputs,"path_weights":weights_df,"horizon_residual_samples":residual_samples,
        "global_corrections":{p:global_corr[p] for p in PATHS},"regime_corrections":{p:regime_corr[p] for p in PATHS},
        "final_corrections":{p:corrections[p] for p in PATHS},"sample_counts":sample_counts,"band_quantiles":pd.DataFrame(quantile_rows),
        "fallback_state":summary_out["fallback_state"],"anchor_price":anchor,"anchor_time":anchor_time,"calculation_timestamp":summary_out["calculation_timestamp"],"source_data_timestamp":summary_out["source_data_timestamp"],
    }
    return {"ok":True,"main":main_df,"red":outputs["red"],"yellow":outputs["yellow"],"blue":outputs["blue"],"raw":base,"summary":summary_out,"audit":audit,"path_weights":weights_df}


def calibrated_candles(bundle: Dict[str,Any], *, anchor_price: float) -> pd.DataFrame:
    if not isinstance(bundle,dict) or not bundle.get("ok"):
        return pd.DataFrame()
    main=bundle.get("main")
    if not isinstance(main,pd.DataFrame) or main.empty:
        return pd.DataFrame()
    rows=[]; previous=float(anchor_price)
    for _,row in main.iterrows():
        close=max(_finite(row.get("main_path"),previous),1e-9); upper=max(_finite(row.get("upper_band"),close),close); lower=min(max(_finite(row.get("lower_band"),close),1e-9),close)
        rows.append({"time":pd.Timestamp(row.get("time")),"open":round(previous,6),"high":round(max(previous,close,upper),6),"low":round(min(previous,close,lower),6),"close":round(close,6),"prediction_step":int(row.get("step",len(rows)+1)),"candle_type":"CALIBRATED_POWERBI_FUTURE","Upper Band":round(upper,6),"Lower Band":round(lower,6),"Calibration Version":CALIBRATION_VERSION})
        previous=close
    return pd.DataFrame(rows)
