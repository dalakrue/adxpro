"""Append-only point-in-time policy decision ledger.

The canonical action is the behavior action.  Historical propensities are never
invented.  Each 1H/2H/3H/6H horizon is a separate versioned record and is only
settled after the corresponding completed H1 candle exists.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import math
import sqlite3

import numpy as np
import pandas as pd

from services.canonical_snapshot_store import DB_PATH

VERSION = "policy-decision-ledger-20260621-v1"
HORIZONS = (1, 2, 3, 6)
ACTIONS = ("BUY", "SELL", "WAIT")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _finite(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _path(source: Mapping[str, Any], paths: Sequence[str], default: Any = None) -> Any:
    for path in paths:
        current: Any = source
        ok = True
        for token in path.split("."):
            if isinstance(current, Mapping) and token in current:
                current = current[token]
            else:
                ok = False
                break
        if ok and current not in (None, ""):
            return current
    return default


def _action(value: Any) -> str:
    text = str(value or "WAIT").upper()
    if "BUY" in text or "LONG" in text:
        return "BUY"
    if "SELL" in text or "SHORT" in text:
        return "SELL"
    return "WAIT"


def _utc(value: Any) -> pd.Timestamp | None:
    stamp = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(stamp) else pd.Timestamp(stamp)


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalise_probability_vector(value: Any) -> dict[str, float] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return None
    if not isinstance(value, Mapping):
        return None
    result: dict[str, float] = {}
    for action in ACTIONS:
        candidate = None
        for key in (action, action.lower(), action.title()):
            if key in value:
                candidate = _finite(value[key])
                break
        if candidate is None or candidate < 0 or candidate > 1:
            return None
        result[action] = candidate
    total = sum(result.values())
    if not 0.999 <= total <= 1.001:
        return None
    return {key: value / total for key, value in result.items()}


def extract_explicit_probability_vectors(canonical: Mapping[str, Any]) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    behavior = _path(canonical, (
        "policy.behavior_action_probabilities", "policy.behavior_probabilities",
        "final_decision.behavior_action_probabilities", "behavior_action_probabilities",
    ))
    candidate = _path(canonical, (
        "policy.candidate_action_probabilities", "policy.candidate_probabilities",
        "final_decision.candidate_action_probabilities", "candidate_action_probabilities",
        "shadow_policy.action_probabilities",
    ))
    return _normalise_probability_vector(behavior), _normalise_probability_vector(candidate)


def _latest_completed_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame(), None
    work = frame.copy(deep=False)
    lookup = {str(c).strip().lower(): c for c in work.columns}
    time_col = next((lookup[k] for k in ("time", "timestamp", "datetime", "date") if k in lookup), None)
    close_col = next((lookup[k] for k in ("close", "closing_price", "price") if k in lookup), None)
    if time_col is None or close_col is None:
        return pd.DataFrame(), None
    work = work.assign(
        __time=pd.to_datetime(work[time_col], errors="coerce", utc=True),
        __close=pd.to_numeric(work[close_col], errors="coerce"),
    ).dropna(subset=["__time", "__close"])
    for name in ("high", "low"):
        col = lookup.get(name)
        work[f"__{name}"] = pd.to_numeric(work[col], errors="coerce") if col else work["__close"]
    work = work.sort_values("__time", kind="mergesort").drop_duplicates("__time", keep="last")
    return work.reset_index(drop=True), str(time_col)


def _canonical_action(canonical: Mapping[str, Any]) -> str:
    return _action(_path(canonical, (
        "final_decision.final_decision", "final_decision.decision", "decision.final_decision",
        "decision.action", "canonical_action", "action",
    ), "WAIT"))


def _candidate_action(canonical: Mapping[str, Any], baseline: str) -> str:
    explicit = _path(canonical, (
        "shadow_policy.candidate_action", "policy.candidate_action", "candidate_action",
    ))
    return _action(explicit) if explicit not in (None, "") else baseline


def _feature_snapshot(canonical: Mapping[str, Any]) -> dict[str, Any]:
    final = _mapping(canonical.get("final_decision"))
    regime = _mapping(canonical.get("regime"))
    reliability = _mapping(canonical.get("reliability"))
    risk = _mapping(canonical.get("risk"))
    priority = _mapping(canonical.get("priority"))
    market = _mapping(canonical.get("market"))
    return {
        "master_score": _path(canonical, ("scores.master", "master_score", "final_decision.master_score")),
        "entry_score": _path(canonical, ("scores.entry", "entry_score", "final_decision.entry_score")),
        "hold_score": _path(canonical, ("scores.hold", "hold_score", "final_decision.hold_score")),
        "tp_score": _path(canonical, ("scores.tp", "tp_score", "final_decision.tp_score")),
        "exit_risk_score": _path(canonical, ("scores.exit_risk", "exit_risk", "final_decision.exit_risk")),
        "market_quality": _path(canonical, ("market_quality.score", "market_quality", "quality.market_quality")),
        "reliability": reliability.get("score") or reliability.get("reliability_pct") or canonical.get("reliability_score"),
        "h1_regime": regime.get("h1") or regime.get("h1_regime") or regime.get("current_regime") or canonical.get("current_regime"),
        "h4_regime": regime.get("h4") or regime.get("h4_regime"),
        "d1_regime": regime.get("d1") or regime.get("d1_regime"),
        "regime_age": regime.get("age") or regime.get("days_since_change") or regime.get("regime_age"),
        "session": market.get("session") or canonical.get("session"),
        "volatility_bucket": market.get("volatility_bucket") or regime.get("volatility_bucket") or canonical.get("volatility_bucket"),
        "spread": risk.get("spread") or market.get("spread") or canonical.get("spread"),
        "forecast_agreement": _path(canonical, ("forecasts.agreement", "forecast_agreement", "reliability.forecast_agreement")),
        "conflict_status": _path(canonical, ("conflict.status", "conflict_status", "regime.conflict_status")),
        "counter_trend_status": _path(canonical, ("counter_trend.status", "counter_trend_status", "regime.counter_trend_status")),
        "priority": priority.get("score") or priority.get("priority_score") or final.get("priority_score"),
        "data_source_version": _path(canonical, ("metadata.data_source_version", "data_source_version", "source_version")),
        "calculation_version_group": _path(canonical, ("metadata.calculation_version", "calculation_version", "model_version")),
    }


def _spread_bucket(spread: float | None) -> str:
    if spread is None:
        return "UNKNOWN"
    # Accept either absolute EURUSD price spread or pip-like units without
    # allowing the larger-unit thresholds to swallow the price-scale branch.
    if spread < 0.01:
        return "LOW" if spread <= 0.00008 else ("MEDIUM" if spread <= 0.00016 else "HIGH")
    return "LOW" if spread <= 0.8 else ("MEDIUM" if spread <= 1.6 else "HIGH")


def _reference_price(canonical: Mapping[str, Any], frame: pd.DataFrame, cutoff: pd.Timestamp | None) -> float | None:
    explicit = _finite(_path(canonical, (
        "market.last_close", "market.reference_entry_price", "reference_entry_price",
        "last_close", "price.last_close",
    )))
    if explicit is not None:
        return explicit
    if cutoff is None or frame.empty:
        return None
    eligible = frame.loc[frame["__time"] <= cutoff]
    return _finite(eligible.iloc[-1]["__close"]) if not eligible.empty else None


def _explicit_costs(canonical: Mapping[str, Any], entry: float | None) -> dict[str, float | None]:
    risk = _mapping(canonical.get("risk"))
    result: dict[str, float | None] = {}
    for name, paths in {
        "spread_cost": ("risk.spread_cost_fraction", "costs.spread_fraction", "spread_cost_fraction"),
        "slippage_cost": ("risk.slippage_cost_fraction", "costs.slippage_fraction", "slippage_cost_fraction"),
        "commission_cost": ("risk.commission_cost_fraction", "costs.commission_fraction", "commission_cost_fraction"),
    }.items():
        result[name] = _finite(_path(canonical, paths))
    # An explicitly published absolute spread can be converted using the point-in-time entry price.
    if result["spread_cost"] is None and entry and entry > 0:
        spread = _finite(risk.get("spread") or _path(canonical, ("market.spread", "spread")))
        if spread is not None and 0 <= spread < 0.01:
            result["spread_cost"] = spread / entry
    return result


def _base_ledger_record(canonical: Mapping[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    features = _feature_snapshot(canonical)
    cutoff = _utc(_path(canonical, (
        "data_cutoff_timestamp", "latest_completed_candle_time", "market.latest_completed_candle_time",
        "metadata.latest_completed_candle_time", "calculation_completed_at",
    )))
    if cutoff is None and not frame.empty:
        cutoff = pd.Timestamp(frame["__time"].max())
    run_id = str(canonical.get("canonical_calculation_id") or canonical.get("run_id") or canonical.get("calculation_generation") or "UNKNOWN")
    decision_id = "DEC-" + _json_hash([run_id, cutoff.isoformat() if cutoff is not None else None, _canonical_action(canonical)])[:24]
    baseline = _canonical_action(canonical)
    candidate = _candidate_action(canonical, baseline)
    behavior_vector, candidate_vector = extract_explicit_probability_vectors(canonical)
    entry = _reference_price(canonical, frame, cutoff)
    costs = _explicit_costs(canonical, entry)
    behavior_prob = behavior_vector.get(baseline) if behavior_vector else None
    candidate_prob = candidate_vector.get(candidate) if candidate_vector else None
    candidate_of_behavior = candidate_vector.get(baseline) if candidate_vector else None
    feature_hash = _json_hash(features)
    return {
        "decision_id": decision_id,
        "calculation_run_id": run_id,
        "decision_timestamp_utc": (cutoff or pd.Timestamp.now(tz="UTC")).isoformat(),
        "symbol": str(canonical.get("symbol") or "EURUSD").upper(),
        "timeframe": str(canonical.get("timeframe") or "H1").upper(),
        "data_cutoff_timestamp": cutoff.isoformat() if cutoff is not None else None,
        "day_of_week": cutoff.day_name().upper() if cutoff is not None else None,
        "feature_snapshot_hash": feature_hash,
        "baseline_version": str(_path(canonical, ("calculation_version", "metadata.calculation_version", "model_version"), "canonical-baseline")),
        "candidate_version": str(_path(canonical, ("shadow_policy.version", "candidate_version"), "shadow-candidate-v1")),
        "baseline_action": baseline,
        "candidate_action": candidate,
        "behavior_action_probability": behavior_prob,
        "candidate_action_probability": candidate_prob,
        "candidate_probability_of_behavior_action": candidate_of_behavior,
        "behavior_probability_vector": behavior_vector,
        "candidate_probability_vector": candidate_vector,
        **features,
        "spread_bucket": _spread_bucket(_finite(features.get("spread"))),
        "reference_entry_price": entry,
        **costs,
        "source_generation_id": run_id,
        "calculation_version": VERSION,
    }


def load_latest_policy_ledger(*, db_path: Path | str = DB_PATH, limit: int = 20000) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame()
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policy_decision_ledger_20260621'"
        ).fetchone()
        if not exists:
            return pd.DataFrame()
        column_rows = conn.execute("PRAGMA table_info(policy_decision_ledger_20260621)").fetchall()
        columns = [str(row[1]) for row in column_rows]
        if not columns:
            return pd.DataFrame()
        quoted = ", ".join(f'p."{name.replace(chr(34), chr(34) * 2)}"' for name in columns)
        outer = ", ".join(f'"{name.replace(chr(34), chr(34) * 2)}"' for name in columns)
        query = f"""
        SELECT {outer} FROM (
          SELECT {quoted}, ROW_NUMBER() OVER (
            PARTITION BY decision_id, evaluation_horizon ORDER BY record_version DESC, evaluated_at DESC
          ) AS __rn
          FROM policy_decision_ledger_20260621 p
        ) WHERE __rn=1 ORDER BY decision_timestamp_utc ASC LIMIT ?
        """
        frame = pd.read_sql_query(query, conn, params=(int(max(1, min(limit, 100000))),))
        frame = frame.drop(columns=["__rn"], errors="ignore")
        if "payload_json" in frame.columns:
            for index, raw in frame["payload_json"].items():
                try:
                    payload = json.loads(raw) if isinstance(raw, str) else {}
                except Exception:
                    payload = {}
                if isinstance(payload, Mapping):
                    for key, value in payload.items():
                        if key not in frame.columns:
                            frame[key] = None
                        if frame.at[index, key] is None or (isinstance(frame.at[index, key], float) and math.isnan(frame.at[index, key])):
                            frame.at[index, key] = value
        return frame
    except Exception:
        return pd.DataFrame()
    finally:
        if conn is not None:
            conn.close()


def _settle_record(record: Mapping[str, Any], frame: pd.DataFrame) -> dict[str, Any] | None:
    status = str(record.get("record_status") or "PENDING").upper()
    if status.startswith("SETTLED"):
        return None
    cutoff = _utc(record.get("data_cutoff_timestamp"))
    horizon = int(_finite(record.get("evaluation_horizon")) or 0)
    entry = _finite(record.get("reference_entry_price"))
    if cutoff is None or horizon not in HORIZONS or entry is None or entry <= 0 or frame.empty:
        return None
    target = cutoff + pd.Timedelta(hours=horizon)
    available = frame.loc[frame["__time"] >= target]
    if available.empty:
        return None
    outcome = available.iloc[0]
    settlement_time = pd.Timestamp(outcome["__time"])
    # Require the full target horizon; a future row before target is never accepted.
    if settlement_time < target:
        return None
    interval = frame.loc[(frame["__time"] > cutoff) & (frame["__time"] <= settlement_time)]
    if interval.empty:
        return None
    close = _finite(outcome["__close"])
    if close is None:
        return None
    action = _action(record.get("baseline_action"))
    direction = 1.0 if action == "BUY" else (-1.0 if action == "SELL" else 0.0)
    gross_fraction = direction * (close - entry) / entry
    high = pd.to_numeric(interval["__high"], errors="coerce")
    low = pd.to_numeric(interval["__low"], errors="coerce")
    if direction > 0:
        mfe = float((high.max() - entry) / entry)
        mae = float((low.min() - entry) / entry)
    elif direction < 0:
        mfe = float((entry - low.min()) / entry)
        mae = float((entry - high.max()) / entry)
    else:
        mfe = mae = 0.0
    costs = [_finite(record.get(name)) for name in ("spread_cost", "slippage_cost", "commission_cost")]
    costs_complete = all(value is not None and value >= 0 for value in costs)
    net_fraction = gross_fraction - sum(value or 0.0 for value in costs) if costs_complete else None
    result = dict(record)
    version = int(_finite(record.get("record_version")) or 1) + 1
    result.update({
        "record_key": f"{record.get('decision_id')}|H{horizon}|V{version}",
        "target_timestamp_utc": target.isoformat(),
        "settlement_timestamp": settlement_time.isoformat(),
        "gross_return": gross_fraction,
        "net_return": net_fraction,
        "net_return_fraction": net_fraction,
        "maximum_adverse_excursion": mae,
        "maximum_favorable_excursion": mfe,
        "drawdown_contribution": min(0.0, net_fraction) if net_fraction is not None else None,
        "record_version": version,
        "record_status": "SETTLED" if costs_complete else "SETTLED_COST_INCOMPLETE",
        "evaluated_at": pd.Timestamp.now(tz="UTC").isoformat(),
    })
    return result


def build_policy_ledger_rows(
    canonical: Mapping[str, Any],
    completed_h1: pd.DataFrame,
    *,
    db_path: Path | str = DB_PATH,
) -> tuple[list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    frame, _ = _latest_completed_frame(completed_h1)
    previous = load_latest_policy_ledger(db_path=db_path)
    rows: list[dict[str, Any]] = []
    for record in previous.to_dict("records") if not previous.empty else []:
        settled = _settle_record(record, frame)
        if settled is not None:
            rows.append(settled)

    base = _base_ledger_record(canonical, frame)
    cutoff = _utc(base.get("data_cutoff_timestamp"))
    now = pd.Timestamp.now(tz="UTC").isoformat()
    for horizon in HORIZONS:
        record = dict(base)
        record.update({
            "record_key": f"{base['decision_id']}|H{horizon}|V1",
            "evaluation_horizon": horizon,
            "target_timestamp_utc": (cutoff + pd.Timedelta(hours=horizon)).isoformat() if cutoff is not None else None,
            "settlement_timestamp": None,
            "gross_return": None,
            "net_return": None,
            "net_return_fraction": None,
            "maximum_adverse_excursion": None,
            "maximum_favorable_excursion": None,
            "drawdown_contribution": None,
            "record_version": 1,
            "record_status": "PENDING",
            "evaluated_at": now,
        })
        rows.append(record)

    latest_rows = previous.to_dict("records") if not previous.empty else []
    by_key = {(str(r.get("decision_id")), int(_finite(r.get("evaluation_horizon")) or 0)): dict(r) for r in latest_rows}
    for row in rows:
        key = (str(row.get("decision_id")), int(_finite(row.get("evaluation_horizon")) or 0))
        old = by_key.get(key)
        if old is None or int(_finite(row.get("record_version")) or 0) >= int(_finite(old.get("record_version")) or 0):
            by_key[key] = dict(row)
    combined = pd.DataFrame(list(by_key.values()))
    if not combined.empty:
        combined = combined.sort_values(["decision_timestamp_utc", "evaluation_horizon"], kind="mergesort").reset_index(drop=True)
    diagnostic = {
        "new_pending_rows": len(HORIZONS),
        "new_settlement_rows": sum(1 for row in rows if str(row.get("record_status")) == "SETTLED"),
        "cost_incomplete_rows": sum(1 for row in rows if str(row.get("record_status")) == "SETTLED_COST_INCOMPLETE"),
        "behavior_propensity_present": base.get("behavior_action_probability") is not None,
        "candidate_propensity_present": base.get("candidate_probability_of_behavior_action") is not None,
        "future_leakage_detected": False,
        "horizons": list(HORIZONS),
        "calculation_version": VERSION,
    }
    return rows, combined, diagnostic


def validate_ledger_point_in_time(frame: pd.DataFrame) -> dict[str, Any]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return {"status": "INSUFFICIENT_EVIDENCE", "valid": False, "premature_settlement_count": 0}
    data = frame.copy(deep=False)
    cutoff = pd.to_datetime(data.get("data_cutoff_timestamp"), errors="coerce", utc=True)
    target = pd.to_datetime(data.get("target_timestamp_utc"), errors="coerce", utc=True)
    settled = pd.to_datetime(data.get("settlement_timestamp"), errors="coerce", utc=True)
    status = data.get("record_status", pd.Series("", index=data.index)).astype(str).str.upper()
    premature = status.str.startswith("SETTLED") & (settled.isna() | target.isna() | settled.lt(target))
    invalid_cutoff = cutoff.isna()
    return {
        "status": "PASS" if not premature.any() and not invalid_cutoff.any() else "FAIL",
        "valid": bool(not premature.any() and not invalid_cutoff.any()),
        "premature_settlement_count": int(premature.sum()),
        "invalid_cutoff_count": int(invalid_cutoff.sum()),
        "row_count": int(len(data)),
    }


__all__ = [
    "VERSION", "HORIZONS", "ACTIONS", "extract_explicit_probability_vectors",
    "load_latest_policy_ledger", "build_policy_ledger_rows", "validate_ledger_point_in_time",
]
