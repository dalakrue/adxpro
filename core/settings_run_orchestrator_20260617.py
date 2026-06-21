"""One-click Settings calculation orchestrator.

This module does not add a prediction model. It calls the project's existing
Lunch, PowerBI, regime, NLP and shared-sync functions once, stores their normal
caches, and then lets the Lunch page render those caches without another Run or
Load button.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Mapping

import pandas as pd
import streamlit as st


REGIME_NLP_HISTORY_DAYS = 25


def _call(ns: Dict[str, Any], name: str, *args: Any, **kwargs: Any) -> Any:
    fn = ns.get(name)
    if not callable(fn):
        raise RuntimeError(f"Existing function {name} is unavailable")
    return fn(*args, **kwargs)


def _build_lunch_metric(ns: Dict[str, Any]) -> Dict[str, Any]:
    result = _call(ns, "_get_cached_lunch_metric_result", True)
    if not isinstance(result, dict):
        return {"ok": False, "message": "Lunch metric returned an unsupported result."}
    if result.get("ok"):
        st.session_state["lunch_show_full_metric_details"] = True
        try:
            _call(ns, "_get_cached_lunch_copy_payload", True)
        except Exception:
            pass
        try:
            scan = _call(ns, "_load_reversal_scan")
            if isinstance(scan, pd.DataFrame) and not scan.empty:
                st.session_state["home_reversal_25d_scan"] = scan
        except Exception:
            pass
    return result


def _build_powerbi(ns: Dict[str, Any], validated_df: pd.DataFrame | None = None) -> Dict[str, Any]:
    rows_limit = int(st.session_state.get("dv_pp_rows", 10000) or 10000)
    horizon = int(st.session_state.get("dv_pp_horizon", 36) or 36)
    min_days = int(st.session_state.get("dv_pp_min_days", 5) or 5)
    bt_lookback = int(st.session_state.get("dv_pp_bt", 180) or 180)

    raw = validated_df if isinstance(validated_df, pd.DataFrame) and not validated_df.empty else _call(ns, "_clean_lunch_visual_df", limit=rows_limit)
    data = _call(ns, "_dv_prepare_ohlc_v20260609", raw, limit=rows_limit)
    if not isinstance(data, pd.DataFrame) or data.empty or len(data) < 120:
        return {
            "ok": False,
            "message": "PowerBI needs at least 120 clean OHLC rows.",
            "rows": int(len(data)) if isinstance(data, pd.DataFrame) else 0,
        }

    base_result = _call(ns, "_five_layer_powerbi_calculate", data, horizon=horizon)
    predicted = _call(ns, "_dv_predict_future_candles_v20260609", data, horizon=horizon)
    bt_hist, bt_summary = _call(ns, "_dv_prediction_vs_actual_history_v20260609", data, lookback=bt_lookback, horizon=1)

    # Deterministic accuracy/reliability post-calibration. The original model
    # outputs are preserved; this adds a shared main path and empirical bands
    # based on completed prediction-vs-actual error and path agreement.
    yellow_current = pd.DataFrame()
    blue_previous = pd.DataFrame()
    yellow_builder = ns.get("_build_last_candle_yellow_6h_projection_v5")
    if callable(yellow_builder):
        try:
            yellow_current = yellow_builder(data, horizon=min(24, horizon), mode="Balanced", risk_filter="Medium")
        except Exception:
            yellow_current = pd.DataFrame()
        try:
            blue_previous = yellow_builder(data.iloc[:-1], horizon=min(24, horizon), mode="Balanced", risk_filter="Medium")
        except Exception:
            blue_previous = pd.DataFrame()
    try:
        from core.powerbi_path_calibration_20260617 import calibrate_projection_bundle, calibrated_candles
        regime_reliability = None
        regime_ctx = st.session_state.get("regime_context_20260614")
        if isinstance(regime_ctx, dict):
            metrics = regime_ctx.get("metrics", {}) if isinstance(regime_ctx.get("metrics"), dict) else {}
            regime_reliability = metrics.get("Regime Reliable Score") or metrics.get("Regime Reliability")
        regime_name = None
        conflict_state = None
        if isinstance(regime_ctx, dict):
            summary_ctx = regime_ctx.get("summary") if isinstance(regime_ctx.get("summary"), dict) else {}
            regime_name = regime_ctx.get("current_regime") or regime_ctx.get("Current Regime") or summary_ctx.get("Current Regime")
            conflict_state = regime_ctx.get("conflict") or regime_ctx.get("transition_risk")
        calibrated_bundle = calibrate_projection_bundle(
            data,
            red=predicted,
            yellow=yellow_current,
            blue=blue_previous,
            horizon=horizon,
            bt_history=bt_hist,
            bt_summary=bt_summary,
            regime_reliability=regime_reliability,
            current_regime=regime_name,
            transition_or_conflict=conflict_state,
            source_data_timestamp=data["time"].iloc[-1] if "time" in data.columns else None,
        )
        # Additive combination upgrade only: existing red/yellow/blue paths and
        # their raw outputs are preserved in the audit. Settled residual MSE,
        # Wiener gain and lagged residual correlation determine adaptive weights
        # before any visual step limiting is applied.
        try:
            from core.powerbi_mmse_weighting_20260618 import upgrade_projection_bundle
            support_cache = st.session_state.get("causal_quant_support_20260618")
            support_cache = support_cache if isinstance(support_cache, dict) else {}
            calibrated_bundle = upgrade_projection_bundle(
                calibrated_bundle,
                market_data=data,
                regime_conditioned_distributions=support_cache.get("regime_conditioned_distributions"),
                transition_state=(support_cache.get("transition_risk") or {}).get("status", conflict_state),
            )
        except Exception as exc:
            calibrated_bundle.setdefault("audit", {})["mmse_weighting_error"] = str(exc)[:240]
        calibrated_prediction = calibrated_candles(
            calibrated_bundle,
            anchor_price=float(data["close"].iloc[-1]),
        )
    except Exception as exc:
        calibrated_bundle = {"ok": False, "message": str(exc)}
        calibrated_prediction = pd.DataFrame()

    projection_history = _call(
        ns,
        "_dv_dynamic_projection_history_v20260609",
        data,
        lookback_days=10,
        horizon=min(6, horizon),
    )
    regime_summary, regime_hist = _call(
        ns,
        "_dv_major_regime_detector_v20260609",
        data,
        min_days=float(min_days),
        lookback_days=240,
        horizon=horizon,
    )
    recent = _call(ns, "_dv_last_continuous_days_v20260609", data, days=10)
    lightblue = _call(ns, "_dv_build_lightblue_path_v20260609", recent, predicted)
    sorter = ns.get("_dv_sort_newest_first_v20260609")
    if callable(sorter):
        bt_hist = sorter(bt_hist)
        regime_hist = sorter(regime_hist)

    signature_fn = ns.get("_lunch_df_signature")
    data_signature = signature_fn() if callable(signature_fn) else (len(data), str(data.iloc[-1].get("time", "")))
    signature = (data_signature, rows_limit, horizon, min_days, bt_lookback, "settings_auto_powerbi_20260617")

    st.session_state.update({
        "lunch_bi_visual_ready": True,
        "dv_pp_df": data,
        "dv_pp_base_result": base_result,
        "dv_pp_predicted": predicted,
        "dv_pp_predicted_calibrated_20260617": calibrated_prediction,
        "powerbi_calibrated_bundle_20260617": calibrated_bundle,
        "powerbi_path_audit_20260618": calibrated_bundle.get("audit", {}) if isinstance(calibrated_bundle, dict) else {},
        "dv_pp_lightblue_path": lightblue,
        "dv_pp_projection_history": projection_history,
        "dv_pp_bt_hist": bt_hist,
        "dv_pp_bt_summary": bt_summary,
        "dv_pp_regime_summary": regime_summary,
        "dv_pp_regime_hist": regime_hist,
        "dv_pp_sig": signature,
        "show_restored_powerbi_20260617": True,
        "load_original_powerbi_from_antd_lunch_20260615": True,
    })
    return {
        "ok": True,
        "rows": int(len(data)),
        "predicted_rows": int(len(predicted)) if isinstance(predicted, pd.DataFrame) else 0,
        "calibrated_rows": int(len(calibrated_prediction)) if isinstance(calibrated_prediction, pd.DataFrame) else 0,
        "path_reliability_pct": ((calibrated_bundle.get("summary") or {}).get("reliability_pct") if isinstance(calibrated_bundle, dict) else None),
        "backtest_rows": int(len(bt_hist)) if isinstance(bt_hist, pd.DataFrame) else 0,
    }


def _source_identity() -> tuple[str, str, str]:
    # Operational decisions in this product are intentionally fixed to the
    # protected EURUSD completed-H1 authority. M1 remains a timing input only.
    source = str(st.session_state.get("data_source") or st.session_state.get("selected_source") or st.session_state.get("source") or "SESSION")
    return "EURUSD", "H1", source


def _preflight_dataframe(ns: Dict[str, Any]) -> pd.DataFrame:
    """Deterministically select a timestamped OHLC source for the Settings run.

    Production decisions never manufacture timestamps and never select merely the
    first non-empty frame.  Candidates are scored by schema validity, explicit
    source preference, row count and latest completed timestamp.
    """
    candidates: list[tuple[str, pd.DataFrame]] = []
    for name, args in (("_clean_lunch_visual_df", (10000,)), ("_prepare_lunch_df", ()), ("_get_lunch_df", ())):
        fn = ns.get(name)
        if callable(fn):
            try:
                value = fn(*args) if args else fn()
            except TypeError:
                try:
                    value = fn(limit=10000)
                except Exception:
                    value = None
            except Exception:
                value = None
            if isinstance(value, pd.DataFrame) and not value.empty:
                candidates.append((name, value))
    for key in ("dv_pp_df", "lunch_5layer_powerbi_df", "last_df", "ohlc_df", "df"):
        value = st.session_state.get(key)
        if isinstance(value, pd.DataFrame) and not value.empty:
            candidates.append((key, value))

    preference = {"_clean_lunch_visual_df": 35, "dv_pp_df": 34, "lunch_5layer_powerbi_df": 32, "last_df": 30, "_prepare_lunch_df": 26, "ohlc_df": 22, "df": 18, "_get_lunch_df": 16}
    best = pd.DataFrame()
    best_score = float("-inf")
    for name, raw in candidates:
        frame = raw
        lower = {str(c).strip().lower(): c for c in frame.columns}
        time_col = next((lower[k] for k in ("time", "datetime", "timestamp", "date_time", "date") if k in lower), None)
        close_col = next((lower[k] for k in ("close", "c") if k in lower), None)
        if time_col is None or close_col is None:
            continue
        parsed = pd.to_datetime(frame[time_col], errors="coerce", utc=True)
        valid_count = int(parsed.notna().sum())
        if valid_count < 30:
            continue
        latest = parsed.max()
        if pd.isna(latest):
            continue
        ohlc_count = sum(1 for key in ("open", "high", "low", "close") if key in lower)
        duplicate_penalty = float(parsed.duplicated().mean() * 40.0)
        score = float(preference.get(name, 0)) + min(valid_count, 10000) / 250.0 + ohlc_count * 4.0 - duplicate_penalty
        # Reject explicitly mismatched identities; missing metadata remains a
        # lower-confidence fallback for legacy frames.
        attrs = getattr(frame, "attrs", {}) or {}
        active_identity = dict(zip(("symbol", "timeframe", "source"), _source_identity()))
        identity_mismatch = False
        for field in ("symbol", "timeframe", "source"):
            declared = attrs.get(field)
            active = active_identity.get(field)
            if declared and active:
                if str(declared).upper() != str(active).upper():
                    identity_mismatch = True
                    break
                score += 8.0
        if identity_mismatch:
            continue
        previous = st.session_state.get("canonical_decision_result_20260617") or {}
        declared_run = attrs.get("run_id")
        declared_signature = attrs.get("data_signature")
        if declared_run and previous.get("run_id"):
            score += 6.0 if str(declared_run) == str(previous.get("run_id")) else -18.0
        if declared_signature and previous.get("data_signature"):
            score += 6.0 if str(declared_signature) == str(previous.get("data_signature")) else -12.0
        if score > best_score:
            best = frame
            best_score = score
            st.session_state["selected_ohlc_source_key_20260617"] = name
            st.session_state["selected_ohlc_latest_time_20260617"] = latest.isoformat()
    return best


def run_settings_calculation(ns: Dict[str, Any]) -> Dict[str, Any]:
    """Build all existing caches once, then atomically publish one canonical result."""
    started = time.time()
    run_started_at = pd.Timestamp.now(tz="UTC").isoformat()
    perf_started = time.perf_counter()
    cpu_started = time.process_time()
    try:
        import psutil
        _process = psutil.Process()
        rss_before = int(_process.memory_info().rss)
    except Exception:
        _process = None
        rss_before = 0
    lock_key = "settings_calculation_lock_20260617"
    lock_time_key = "settings_calculation_lock_time_20260617"
    now = time.time()
    if st.session_state.get(lock_key) and now - float(st.session_state.get(lock_time_key, 0) or 0) < 300:
        return {
            "ok": False, "duplicate_blocked": True,
            "errors": ["A calculation is already running; duplicate execution was blocked."],
            "built_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    st.session_state[lock_key] = True
    st.session_state[lock_time_key] = now

    symbol, timeframe, source = _source_identity()
    status: Dict[str, Any] = {
        "ok": True, "metric": {}, "powerbi": {}, "data_quality": {}, "ledger": {},
        "canonical": {}, "calibration": {}, "drift": {}, "errors": [],
    }
    nlp_result: Dict[str, Any] = {}
    research_pack: Dict[str, Any] = {}
    detail_tables: Dict[str, Any] = {}
    standards = pd.DataFrame()
    trust_store = None
    regime_trust_history_bundle: Dict[str, Any] = {}
    try:
        from core.operational_sync_20260618 import clear_operational_errors
        clear_operational_errors(st.session_state)
    except Exception:
        pass
    try:
        from core.decision_product_engine_20260617 import validate_data_quality
        from core.prediction_ledger_20260617 import get_prediction_ledger
        ledger = get_prediction_ledger()
        preflight = _preflight_dataframe(ns)
        quality, clean_preflight = validate_data_quality(
            preflight, symbol=symbol, timeframe=timeframe, source=source,
        )
        status["data_quality"] = {
            "status": quality.status, "score": quality.score,
            "warnings": quality.warnings, "blocking_reasons": quality.blocking_reasons,
        }
        # Additive declarative gate. It never repairs prices. A rejected source
        # generation is recorded while the prior completed canonical pointer stays
        # untouched.
        from core.canonical_data_validation_20260621 import validate_source_frame
        research_validation_preflight = validate_source_frame(
            clean_preflight,
            symbol=symbol,
            timeframe=timeframe,
            source=source,
            source_row_count=len(preflight) if isinstance(preflight, pd.DataFrame) else None,
        )
        status["research_data_validation"] = {
            "status": research_validation_preflight.status,
            "generation_id": research_validation_preflight.generation_id,
            "critical_failure_count": research_validation_preflight.critical_failure_count,
            "warning_count": research_validation_preflight.warning_count,
            "failed_constraints": research_validation_preflight.failed_constraints,
        }
        if not research_validation_preflight.publication_allowed:
            from core.research_validation_store_20260621 import record_rejected_generation
            previous_valid = st.session_state.get("canonical_decision_result")
            previous_valid = previous_valid if isinstance(previous_valid, Mapping) else {}
            status["research_validation_rejection"] = record_rejected_generation(
                research_validation_preflight,
                reason="Pre-calculation declarative data validation rejected the generation.",
                previous_valid=previous_valid,
            )
            status["ok"] = False
            status["errors"].append("Research validation gate rejected source data; previous canonical generation was preserved.")
            st.session_state["research_validation_diagnostic_20260621"] = research_validation_preflight.as_dict()
            return status
        # Settlements use only completed candles and run before a new prediction is written.
        status["outcome_settlement"] = ledger.settle_pending_outcomes(clean_preflight)
        status["ledger"] = ledger.health()
        try:
            from core.trust_history_20260619 import get_trust_history_store
            trust_store = get_trust_history_store()
            status["trust_history_settlement"] = trust_store.settle_pending(clean_preflight)
        except Exception as exc:
            trust_store = None
            status["trust_history_settlement"] = {"ok": False, "error": str(exc)}
            status["errors"].append(f"Settled trust history: {exc}")

        if quality.status == "FAIL_ALL":
            failed_run_id = f"FAILED-{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%S')}-{int(time.time()*1000)%1000000:06d}"
            ledger.record_failed_run({
                "run_id": failed_run_id,
                "created_at": pd.Timestamp.utcnow().isoformat(),
                "symbol": symbol, "timeframe": timeframe, "source": source,
                "data_signature": "preflight-failed", "model_version": "existing-models-v1",
                "calculation_version": "decision-product-20260617-v1", "schema_version": "2.0.0",
                "data_quality": {"status": quality.status}, "calculation_status": "FAILED",
                "failure_reason": "; ".join(quality.blocking_reasons),
                "market": {"latest_completed_candle_time": None},
            })
            status["ok"] = False
            status["errors"].append("Data quality FAIL_ALL: " + "; ".join(quality.blocking_reasons))
            st.session_state["canonical_decision_attempt_20260617"] = {
                "run_id": failed_run_id, "calculation_status": "FAILED",
                "failure_reason": "; ".join(quality.blocking_reasons),
                "data_quality": status["data_quality"],
            }
            return status

        # One private staging frame is the only OHLC input for this calculation.
        # It is not published to legacy keys until the complete canonical run succeeds.
        clean_preflight = clean_preflight.copy(deep=False)
        clean_preflight.attrs.update({"symbol": symbol, "timeframe": timeframe, "source": source, "validation_status": quality.status})
        periodicity_precomputed = {}
        periodicity_frame_precomputed = pd.DataFrame()
        try:
            from core.research_risk_stack_20260619 import build_periodicity_normalization
            settled_for_periodicity = trust_store.frame(status="SETTLED", limit=20000) if trust_store is not None else pd.DataFrame()
            periodicity_precomputed, periodicity_frame_precomputed = build_periodicity_normalization(
                clean_preflight, settled=settled_for_periodicity
            )
            if isinstance(periodicity_frame_precomputed, pd.DataFrame) and not periodicity_frame_precomputed.empty:
                time_col = next((c for c in clean_preflight.columns if str(c).strip().lower() in {"time", "timestamp", "datetime", "date"}), None)
                source_time = pd.to_datetime(clean_preflight[time_col] if time_col else clean_preflight.index, errors="coerce", utc=True)
                normalised = periodicity_frame_precomputed.reindex(pd.DatetimeIndex(source_time))
                for column in (
                    "hour_of_week", "expected_hourly_volatility", "periodicity_normalized_return",
                    "periodicity_normalized_range", "periodicity_normalized_atr",
                    "periodicity_normalized_volume", "periodicity_normalized_residual",
                    "periodicity_sample_count", "periodicity_reliability",
                ):
                    if column in normalised.columns:
                        clean_preflight[column] = normalised[column].to_numpy()
            status["periodicity_normalization"] = {
                "ok": True,
                "status": periodicity_precomputed.get("status"),
                "causal_shift_applied": periodicity_precomputed.get("causal_shift_applied", False),
                "sample_count": periodicity_precomputed.get("periodicity_sample_count", 0),
            }
        except Exception as exc:
            periodicity_precomputed = {}
            periodicity_frame_precomputed = pd.DataFrame()
            status["periodicity_normalization"] = {"ok": False, "optional": True, "message": str(exc)}
        st.session_state["calculation_staging_ohlc_df_20260617"] = clean_preflight

        if quality.status == "FAIL_MODEL":
            st.session_state["data_quality_disabled_models_20260617"] = list(quality.model_disabled)
            status["errors"].append(
                "Data quality FAIL_MODEL: affected models are blocked in the final policy ("
                + ", ".join(quality.model_disabled or ["unspecified model group"]) + ")"
            )
        else:
            st.session_state["data_quality_disabled_models_20260617"] = []

        try:
            from ui.home_master_control_bar_20260615 import run_home_calculation_gate
            run_home_calculation_gate()
        except Exception:
            for key in ("metric_run_calculate", "research_run_calculate", "other_run_calculate"):
                st.session_state[key] = True

        st.session_state.update({
            "metric_run_calculate": True,
            "research_run_calculate": True,
            "other_run_calculate": True,
            "lunch_force_reversal_scan": True,
            "lunch_run_visualization": True,
            "lunch_bi_visual_ready": True,
            "show_restored_original_lunch_20260617": True,
            "show_restored_metric_detail_20260617": True,
            "show_restored_metric_history_20260617": True,
            "show_restored_powerbi_20260617": True,
            "settings_auto_open_lunch_20260617": True,
            "dinner_load_original_advanced_details_20260614": True,
            "dinner_auto_sync_from_main_run_20260617": True,
            "regime_auto_sync_from_main_run_20260617": True,
        })

        try:
            status["metric"] = _build_lunch_metric(ns)
            if not status["metric"].get("ok"):
                status["ok"] = False
                status["errors"].append(status["metric"].get("message", "Lunch metric was not ready."))
        except Exception as exc:
            status["ok"] = False
            status["metric"] = {"ok": False, "message": str(exc)}
            status["errors"].append(f"Lunch metric: {exc}")

        try:
            status["powerbi"] = _build_powerbi(ns, validated_df=clean_preflight)
            if not status["powerbi"].get("ok"):
                status["ok"] = False
                status["errors"].append(status["powerbi"].get("message", "PowerBI was not ready."))
        except Exception as exc:
            status["ok"] = False
            status["powerbi"] = {"ok": False, "message": str(exc)}
            status["errors"].append(f"PowerBI: {exc}")

        # NLP, Data Analysis and Data Mining are built in this same Settings
        # transaction. Finnhub remains optional; cached/persisted 10-day real
        # news is used honestly when the live source returns fewer rows.
        try:
            from ui.nlp_research_panel import run_nlp_analysis
            nlp_result = run_nlp_analysis(force_news=False, use_finbert=False)
            articles = nlp_result.get("articles") if isinstance(nlp_result, dict) else None
            status["nlp"] = {
                "ok": bool(nlp_result),
                "source": "cached/local or optional Finnhub",
                "article_rows": int(len(articles)) if isinstance(articles, pd.DataFrame) else 0,
                "window_days": 10,
            }
        except Exception as exc:
            nlp_result = {}
            status["nlp"] = {"ok": False, "message": str(exc)}
            status["errors"].append(f"NLP: {exc}")
        try:
            from tabs.research import build_all_research_pack_for_settings
            research_pack = build_all_research_pack_for_settings(clean_preflight, nlp_result=nlp_result)
            status["research"] = {
                "ok": bool(research_pack.get("all_inner_tabs_ready")),
                "data_analysis": bool((research_pack.get("data_analysis") or {}).get("ok")),
                "data_mining": bool((research_pack.get("data_mining") or {}).get("ok")),
                "nlp": bool(research_pack.get("nlp")),
            }
        except Exception as exc:
            research_pack = {}
            status["research"] = {"ok": False, "message": str(exc)}
            status["errors"].append(f"Research/Data Mining: {exc}")

        # Prime the deepest existing regime/reliability caches once inside the
        # main Settings workflow. Dinner/Regime renderers only read these caches
        # and never expose another Run or Load control.
        status["inner_sections"] = {}
        for builder_name, label in (
            ("build_reliability_control_center_20260614", "reliability"),
            ("build_regime_context_20260614", "regime"),
        ):
            builder = ns.get(builder_name)
            if callable(builder):
                try:
                    built = builder(force=True)
                    status["inner_sections"][label] = {"ok": bool(built), "source": builder_name}
                except TypeError:
                    try:
                        built = builder(True)
                        status["inner_sections"][label] = {"ok": bool(built), "source": builder_name}
                    except Exception as exc:
                        status["inner_sections"][label] = {"ok": False, "message": str(exc)}
                        status["errors"].append(f"{label.title()} inner cache: {exc}")
                except Exception as exc:
                    status["inner_sections"][label] = {"ok": False, "message": str(exc)}
                    status["errors"].append(f"{label.title()} inner cache: {exc}")
            else:
                status["inner_sections"][label] = {"ok": False, "message": "Existing builder unavailable"}

        try:
            from core.adx_shared_sync_20260615 import ensure_shared_calculation_result
            legacy_shared = ensure_shared_calculation_result(force=True)
        except Exception as exc:
            legacy_shared = {}
            status["errors"].append(f"Shared sync: {exc}")

        try:
            from core.regime_sync_20260617 import canonical_regime_snapshot, regime_standard_table, regime_standard_detail_tables
            canonical_regime_snapshot(days=25)
            standards = regime_standard_table(force=True)
            detail_tables = regime_standard_detail_tables(force=False)
            status["regime_detail_tables"] = {k: int(len(v)) for k, v in detail_tables.items() if isinstance(v, pd.DataFrame)}
            st.session_state["regime_standard_table_20260617"] = standards
            st.session_state["regime_standard_detail_tables_published_20260618"] = detail_tables
            # Carry the existing 1-day, 5-day and 25-day standards into the same
            # immutable result instead of letting the Regime page calculate a
            # second, newer copy after Lunch/PowerBI have already finished.
            if isinstance(legacy_shared, dict) and isinstance(standards, pd.DataFrame) and not standards.empty:
                regime_payload = legacy_shared.setdefault("regime", {})
                for _, row in standards.iterrows():
                    label = str(row.get("Standard", "")).lower()
                    value = str(row.get("Major Regime", "UNKNOWN") or "UNKNOWN")
                    if "lower" in label:
                        regime_payload["lower_standard_regime"] = value
                    elif "middle" in label:
                        regime_payload["middle_standard_regime"] = value
                    elif "higher" in label:
                        regime_payload["higher_standard_regime"] = value
                regime_payload["standards"] = standards.to_dict("records")
        except Exception as exc:
            status["errors"].append(f"Regime sync: {exc}")

        canonical_priority_table = pd.DataFrame()
        try:
            from core.regime_sync_20260617 import merged_hourly_regime_nlp_priority
            canonical_priority_table = merged_hourly_regime_nlp_priority(days=REGIME_NLP_HISTORY_DAYS)
            status["canonical_priority_rows"] = int(len(canonical_priority_table)) if isinstance(canonical_priority_table, pd.DataFrame) else 0
        except Exception as exc:
            status["errors"].append(f"Canonical 25-day priority table: {exc}")

        # One causal 600-row Alpha/Delta history feeds all three regime standards.
        try:
            from core.regime_window_analytics_20260618 import build_regime_window_analytics
            legacy_regime = legacy_shared.get("regime", {}) if isinstance(legacy_shared, dict) and isinstance(legacy_shared.get("regime"), dict) else {}
            existing_regime = legacy_regime.get("current") or legacy_regime.get("current_regime") or ""
            existing_rel = ((legacy_shared.get("reliability") or {}).get("score", 50) if isinstance(legacy_shared, dict) else 50)
            window_analytics = build_regime_window_analytics(clean_preflight, existing_regime=str(existing_regime), existing_reliability=float(existing_rel or 50))
            st.session_state["regime_window_analytics_20260618"] = window_analytics
            if isinstance(legacy_shared, dict):
                legacy_shared.setdefault("regime", {})["window_analytics"] = window_analytics
                legacy_shared["regime_window_analytics"] = window_analytics
                bundle = st.session_state.get("powerbi_calibrated_bundle_20260617")
                if isinstance(bundle, dict):
                    legacy_shared.setdefault("powerbi", {})["calibrated_bundle"] = bundle
            status["regime_window_analytics"] = {"ok": bool(window_analytics.get("ok")), "rows": int(window_analytics.get("actual_history_rows", 0))}
        except Exception as exc:
            status["errors"].append(f"Regime window analytics: {exc}")

        try:
            from core.decision_product_engine_20260617 import build_decision_result, serialize_result
            from core.canonical_runtime_20260617 import proposed_generation, publish_canonical_atomically
            from core.full_metric_canonical_adapter_20260618 import (
                apply_canonical_confirmations,
                build_full_metric_authority,
                enrich_canonical_payload,
            )
            final_df = clean_preflight
            generation = proposed_generation(st.session_state)

            # The 25-day regime/NLP table remains a confirmation source. The
            # canonical priority table itself is ranked from the protected Full
            # Metric history, so no downstream tab can calculate another bias.
            confirmation_priority_table = canonical_priority_table
            full_metric_authority = build_full_metric_authority(
                status.get("metric") or {},
                final_df,
                symbol=symbol,
                timeframe=timeframe,
                legacy_shared=legacy_shared,
                confirmation_table=confirmation_priority_table,
                data_quality_status=quality.status,
            )
            # Causal Research support is computed once from completed H1 rows and
            # protected Full Metric history. It cannot create or reverse a
            # direction; it only enriches candidates and may force WAIT.
            try:
                from core.causal_quant_support_20260618 import (
                    apply_support_to_authority,
                    build_causal_support_bundle,
                    public_support_view,
                )
                previous_support = st.session_state.get("causal_quant_support_20260618")
                previous_support = previous_support if isinstance(previous_support, dict) else {}
                causal_support = build_causal_support_bundle(
                    final_df,
                    full_metric_authority.get("priority_table"),
                    context=legacy_shared,
                    previous_cache=previous_support,
                )
                full_metric_authority = apply_support_to_authority(full_metric_authority, causal_support)
                st.session_state["causal_quant_support_20260618"] = causal_support
                public_causal_support = public_support_view(causal_support)
                if isinstance(legacy_shared, dict):
                    legacy_shared["research_support"] = public_causal_support
                    legacy_shared.setdefault("data_mining", {})["causal_quant_support"] = public_causal_support
                research_pack = st.session_state.get("research_pack_20260612")
                if isinstance(research_pack, dict):
                    research_pack["causal_quant_support"] = public_causal_support
                    st.session_state["research_pack_20260612"] = research_pack
                status["causal_support"] = {
                    "ok": True,
                    "cache_status": causal_support.get("cache_status"),
                    "rows": causal_support.get("retained_rows"),
                    "pattern": (causal_support.get("pattern_memory") or {}).get("pattern_confirmation"),
                    "transition": (causal_support.get("transition_risk") or {}).get("status"),
                    "actionability": (causal_support.get("actionability") or {}).get("current_label"),
                }
            except Exception as exc:
                causal_support = {
                    "version": "causal-quant-support-20260618-v1",
                    "cache_status": "SAFE_FALLBACK",
                    "pattern_memory": {"pattern_confirmation": "NEUTRAL", "pattern_confidence": 0.0},
                    "transition_risk": {"status": "WATCH", "value": 0.5},
                    "actionability": {"current_label": "WATCH", "status": "FAILED SAFELY"},
                    "failure": str(exc)[:300],
                }
                st.session_state["causal_quant_support_20260618"] = causal_support
                status["errors"].append(f"Causal Research support: {exc}")
            canonical_priority_table = full_metric_authority["priority_table"]
            canonical_obj = build_decision_result(
                legacy_shared=legacy_shared, ohlc=final_df, symbol=symbol,
                timeframe=timeframe, source=source, ledger=ledger,
                calculation_generation=generation,
                full_metric_snapshot=full_metric_authority["snapshot"],
            )
            canonical_base = serialize_result(canonical_obj)
            try:
                from core.causal_quant_support_20260618 import apply_support_to_canonical
                canonical_base = apply_support_to_canonical(canonical_base, causal_support)
            except Exception as exc:
                canonical_base.setdefault("metadata", {})["causal_support_apply_error"] = str(exc)[:240]
                canonical_base.setdefault("final_decision", {}).setdefault("blocking_reasons", []).append(
                    "Causal support failed safely; entry remains conservatively gated"
                )
                canonical_base["final_decision"]["final_decision"] = "WAIT"
                canonical_base["final_decision"]["tradeability_decision"] = "WAIT"
                canonical_base["final_decision"]["less_risky_decision"] = "WAIT"

            # Additive multi-scale volatility/risk calibration.  This layer never
            # changes the protected Full Metric formulas or the central red/yellow/
            # blue path.  It is calculated once inside this Settings transaction
            # and is then reused by every existing tab through the canonical adapter.
            from core.multiscale_probabilistic_upgrade_20260618 import (
                build_and_apply_upgrade,
                enrich_existing_regime_tables,
                invariant_report,
            )
            previous_upgrade = st.session_state.get("multiscale_probabilistic_upgrade_20260618")
            previous_upgrade = previous_upgrade if isinstance(previous_upgrade, dict) else {}
            canonical_base, upgrade_cache, upgraded_bundle = build_and_apply_upgrade(
                canonical_base,
                ohlc=final_df,
                calibrated_bundle=st.session_state.get("powerbi_calibrated_bundle_20260617"),
                prediction_history=st.session_state.get("dv_pp_bt_hist"),
                previous_cache=previous_upgrade,
            )
            st.session_state["multiscale_probabilistic_upgrade_20260618"] = upgrade_cache

            # Ten-paper causal calibration runs once inside the same Settings
            # transaction. It is optional and fail-safe: Full Metric History and
            # the previously valid canonical result remain publishable if this
            # enrichment fails. The red/yellow/blue central paths are preserved;
            # only empirical bands, uncertainty and validation metadata are added.
            research_result = {}
            # One bounded settled-evidence frame is reused by the second-generation
            # reliability/shift transaction. It is populated by the existing
            # research settlement block and never stored as another session-state
            # DataFrame.
            settled_research_predictions = pd.DataFrame()
            try:
                from core.research_calibration_20260618 import (
                    ResearchStore,
                    build_research_layer_fail_safe,
                )
                research_store = ResearchStore()
                experiment_matrix, _, _ = research_store.performance_matrix()
                conformal_settlement = research_store.settle_conformal_predictions(final_df)
                research_outcomes = research_store.completed_conformal_outcomes(limit=5000)
                ledger_outcomes = ledger.settled_predictions(symbol=symbol, timeframe=timeframe, limit=6000)
                completed_sources = [frame for frame in (ledger_outcomes, research_outcomes) if isinstance(frame, pd.DataFrame) and not frame.empty]
                settled_research_predictions = pd.concat(completed_sources, ignore_index=True, sort=False) if completed_sources else pd.DataFrame()
                status["research_conformal_settlement"] = conformal_settlement
                previous_research = st.session_state.get("research_calibration_20260618")
                previous_research = previous_research if isinstance(previous_research, dict) else {}
                canonical_base, research_result, upgraded_bundle, research_layer_status = build_research_layer_fail_safe(
                    canonical_base,
                    ohlc=final_df,
                    calibrated_bundle=upgraded_bundle,
                    prediction_history=st.session_state.get("dv_pp_bt_hist"),
                    settled_predictions=settled_research_predictions,
                    previous_cache=previous_research,
                    experiment_performance_matrix=experiment_matrix,
                    # PBO/DSR remain honestly UNAVAILABLE until the registry has
                    # enough tested configurations and aligned realised returns.
                    strategy_returns=None,
                    number_of_trials=None,
                    sharpe_trials=None,
                )
                if research_layer_status.get("ok"):
                    st.session_state["research_calibration_20260618"] = research_result
                    status["research_calibration"] = {
                        "ok": True,
                        "calculation_id": research_result.get("canonical_calculation_id"),
                        "validation_status": research_result.get("validation_status"),
                        "residual_vectors": (research_result.get("conformal_prediction") or {}).get("residual_vector_count"),
                        "pbo_status": (research_result.get("pbo") or {}).get("status"),
                        "dsr_status": (research_result.get("dsr") or {}).get("validation_label"),
                        "invariants": research_result.get("invariants"),
                    }
                else:
                    status["research_calibration"] = {"ok": False, "optional": True, **research_layer_status}
            except Exception as exc:
                canonical_base.setdefault("metadata", {})["research_calibration_error"] = str(exc)[:500]
                canonical_base.setdefault("metadata", {})["research_calibration_status"] = "FAILED SAFELY"
                status["research_calibration"] = {"ok": False, "optional": True, "message": str(exc)}

            # Lightweight ten-concept risk stack. It consumes only completed H1
            # candles, settled forecasts and the protected Full Metric authority.
            # It cannot create/reverse direction; it may only confirm, downgrade,
            # or force WAIT. All outputs are computed once in this transaction.
            research_risk_result = {}
            try:
                from core.research_risk_stack_20260619 import (
                    build_and_apply_research_risk_stack,
                    enrich_metric_history,
                )
                previous_risk = st.session_state.get("research_risk_stack_20260619")
                previous_risk = previous_risk if isinstance(previous_risk, dict) else {}
                canonical_base, research_risk_result, risk_priority_table, upgraded_bundle = build_and_apply_research_risk_stack(
                    canonical_base,
                    ohlc=final_df,
                    trust_store=trust_store,
                    priority_table=full_metric_authority.get("priority_table"),
                    calibrated_bundle=upgraded_bundle,
                    previous_cache=previous_risk,
                    precomputed_periodicity=periodicity_precomputed,
                    precomputed_periodicity_frame=periodicity_frame_precomputed,
                )
                st.session_state["research_risk_stack_20260619"] = research_risk_result
                if isinstance(risk_priority_table, pd.DataFrame) and not risk_priority_table.empty:
                    full_metric_authority["priority_table"] = risk_priority_table
                    status["metric"] = enrich_metric_history(status.get("metric") or {}, risk_priority_table)
                status["research_risk_stack"] = {
                    "ok": True,
                    "version": research_risk_result.get("version"),
                    "periodicity_status": (research_risk_result.get("periodicity") or {}).get("status"),
                    "proper_scoring_status": (research_risk_result.get("proper_scoring") or {}).get("status"),
                    "competing_risk_status": (research_risk_result.get("competing_risk") or {}).get("status"),
                    "trust_status": (research_risk_result.get("confidence_sequence") or {}).get("trust_status"),
                    "selective_pass": (research_risk_result.get("selective_prediction") or {}).get("selective_prediction_pass"),
                    "evt_sufficient": (research_risk_result.get("evt_tail") or {}).get("evt_sample_sufficient"),
                    "event_cluster_level": (research_risk_result.get("event_intensity") or {}).get("event_cluster_level"),
                }
            except Exception as exc:
                canonical_base.setdefault("metadata", {})["research_risk_stack_status"] = "FAILED SAFELY"
                canonical_base["metadata"]["research_risk_stack_error"] = str(exc)[:500]
                status["research_risk_stack"] = {"ok": False, "optional": True, "message": str(exc)}
                status["errors"].append(f"Research risk stack: {exc}")

            if isinstance(upgraded_bundle, dict):
                st.session_state["powerbi_calibrated_bundle_20260617"] = upgraded_bundle
                try:
                    from core.powerbi_path_calibration_20260617 import calibrated_candles
                    anchor = float(pd.to_numeric(final_df["close"], errors="coerce").dropna().iloc[-1])
                    st.session_state["dv_pp_predicted_calibrated_20260617"] = calibrated_candles(
                        upgraded_bundle, anchor_price=anchor
                    )
                except Exception as exc:
                    canonical_base.setdefault("metadata", {})["probabilistic_candle_refresh_error"] = str(exc)[:240]
            detail_tables, standards = enrich_existing_regime_tables(
                detail_tables, standards if isinstance(standards, pd.DataFrame) else pd.DataFrame(),
                canonical_base.get("multiscale_regime") or {},
                str(canonical_base.get("canonical_calculation_id") or ""),
            )
            st.session_state["regime_standard_detail_tables_20260617"] = detail_tables
            st.session_state["regime_standard_detail_tables_published_20260618"] = detail_tables
            st.session_state["regime_standard_table_20260617"] = standards
            status["multiscale_probabilistic_upgrade"] = {
                "ok": True,
                "calculation_id": canonical_base.get("canonical_calculation_id"),
                "volatility_regime": (canonical_base.get("multiscale_regime") or {}).get("current_volatility_regime"),
                "invariants": invariant_report(canonical_base),
            }
            full_metric_authority = apply_canonical_confirmations(
                full_metric_authority, canonical_base
            )
            # Refresh only the candidate display/status aliases after the existing
            # canonical gates settle. Protected Full Metric formulas and direction
            # remain untouched; this keeps Lunch, Dinner, Finder and AI identical.
            try:
                from core.causal_quant_support_20260618 import apply_support_to_authority
                full_metric_authority = apply_support_to_authority(full_metric_authority, causal_support)
            except Exception as exc:
                canonical_base.setdefault("metadata", {})["candidate_support_refresh_error"] = str(exc)[:240]
            canonical_priority_table = full_metric_authority["priority_table"]
            canonical = enrich_canonical_payload(canonical_base, full_metric_authority)
            canonical["calculation_started_at"] = run_started_at
            try:
                from core.trust_history_20260619 import enrich_canonical_with_trust, get_trust_history_store
                trust_store = trust_store or get_trust_history_store()
                canonical = enrich_canonical_with_trust(canonical, trust_store)
                # Include the forecasts about to be recorded as pending, never as settled.
                trust_summary = canonical.get("trust_validation") if isinstance(canonical.get("trust_validation"), dict) else {}
                trust_summary["pending_sample_count"] = int(trust_summary.get("pending_sample_count") or 0) + len(
                    ((canonical.get("forecasts") or {}).get("horizons") or {})
                )
                canonical["trust_validation"] = trust_summary
                status["trust_validation"] = {
                    "ok": True,
                    "settled_samples": trust_summary.get("settled_sample_count", 0),
                    "pending_samples": trust_summary.get("pending_sample_count", 0),
                    "classification": trust_summary.get("trust_classification", "INSUFFICIENT"),
                }
            except Exception as exc:
                canonical.setdefault("metadata", {})["trust_validation_error"] = str(exc)[:300]
                status["trust_validation"] = {"ok": False, "error": str(exc)}
                status["errors"].append(f"Trust validation: {exc}")
            # Build the display-only aggregate position-sizing guardrail from
            # current account/risk settings. It never changes protected trading
            # formulas or the BUY/SELL/WAIT decision.
            try:
                from services.position_sizing import build_risk_plan
                canonical["risk_plan"] = build_risk_plan(st.session_state, canonical)
                status["risk_plan"] = {
                    "ok": True,
                    "status": canonical["risk_plan"].get("status"),
                    "recommended_lots": canonical["risk_plan"].get("recommended_lots"),
                }
            except Exception as exc:
                canonical["risk_plan"] = {"status": "BLOCK", "reason": f"Position sizing unavailable: {exc}", "recommended_lots": 0.0}
                status["errors"].append(f"Position sizing guardrail: {exc}")

            # Decision 11 is a read-only interpretation of the already completed
            # canonical outputs. It appends one published support decision and never
            # changes or reweights the protected original ten decisions.
            try:
                from core.medium_standard_regime_bias_20260619 import build_medium_standard_regime_bias
                canonical["medium_standard_regime_bias"] = build_medium_standard_regime_bias(canonical)
                status["medium_standard_regime_bias"] = {
                    "ok": True,
                    "decision": canonical["medium_standard_regime_bias"].get("decision"),
                    "score": canonical["medium_standard_regime_bias"].get("score"),
                }
            except Exception as exc:
                canonical["medium_standard_regime_bias"] = {
                    "decision_number": 11, "name": "Medium-Standard Regime Bias",
                    "decision": "WAIT", "score": 5.0, "confidence_class": "Weak",
                    "primary_reason": "Published canonical inputs were incomplete.",
                    "conflict_warning": str(exc)[:240], "read_only_support": True,
                    "protected_ten_decisions_changed": False,
                }
                status["medium_standard_regime_bias"] = {"ok": False, "message": str(exc)}

            # Similar-Day Intelligence is calculated once from this transaction's
            # completed H1 authority, then embedded in the same canonical payload.
            # Lunch Field 4 is display-only and never calls this builder.
            similar_day_feature_rows = []
            try:
                from core.similar_day_intelligence_20260619 import build_similar_day_intelligence
                similar_day_result = build_similar_day_intelligence(
                    final_df, canonical, history_table=canonical_priority_table,
                    forecast_history=st.session_state.get("dv_pp_bt_hist"),
                    state=st.session_state,
                )
                similar_day_result = dict(similar_day_result) if isinstance(similar_day_result, dict) else {}
                similar_day_feature_rows = list(similar_day_result.pop("_feature_store_rows", []) or [])
                canonical["similar_day_intelligence"] = similar_day_result
                status["similar_day_intelligence"] = {
                    "ok": bool(similar_day_result.get("ok")),
                    "status": similar_day_result.get("status"),
                    "candidate_rows": len(similar_day_result.get("history_25") or []),
                    "top_five_rows": len(similar_day_result.get("top_five") or []),
                    "reliability": similar_day_result.get("reliability"),
                    "cache_status": similar_day_result.get("cache_status"),
                    "duration_seconds": similar_day_result.get("calculation_duration_seconds"),
                }
                st.session_state["similar_day_intelligence_20260619"] = similar_day_result
            except Exception as exc:
                similar_day_result = {
                    "ok": False, "status": "Unavailable",
                    "message": "The completed generation did not contain enough valid, aligned EURUSD H1 history for Similar-Day Intelligence. Existing Lunch data remains available.",
                    "engine_version": "similar-day-engine-20260619-v1",
                    "feature_version": "similar-day-features-20260619-v1",
                    "calculated_at": pd.Timestamp.now(tz="UTC").isoformat(),
                    "latest_completed_h1_timestamp": canonical.get("latest_completed_candle_time"),
                    "calculation_generation": canonical.get("calculation_generation"),
                }
                canonical["similar_day_intelligence"] = similar_day_result
                st.session_state["similar_day_intelligence_20260619"] = similar_day_result
                st.session_state["similar_day_technical_error_20260619"] = repr(exc)
                status["similar_day_intelligence"] = {"ok": False, "status": "Unavailable", "message": str(exc)}
                status["errors"].append(f"Similar-Day Intelligence: {exc}")

            # Second-generation Advanced Reliability and Distribution-Shift Layer.
            # This is the single hidden versioned research transaction: it runs
            # after settled forecast evidence and the complete canonical object are
            # available, but before atomic canonical publication. It reuses this
            # transaction's completed H1 frame and one bounded settled frame.
            advanced_reliability_result = {}
            advanced_reliability_store = None
            try:
                from core.advanced_reliability_shift_20260620 import (
                    AdvancedReliabilityStore,
                    build_advanced_reliability_transaction,
                )
                advanced_reliability_store = AdvancedReliabilityStore()
                if not isinstance(settled_research_predictions, pd.DataFrame) or settled_research_predictions.empty:
                    settled_research_predictions = (
                        trust_store.frame(status="SETTLED", limit=6000)
                        if trust_store is not None else pd.DataFrame()
                    )
                canonical, advanced_reliability_result, advanced_stage = build_advanced_reliability_transaction(
                    canonical,
                    completed_h1=final_df,
                    settled_predictions=settled_research_predictions,
                    store=advanced_reliability_store,
                    previous=st.session_state.get("advanced_reliability_shift_20260620"),
                    persist_stage=True,
                )
                st.session_state["advanced_reliability_shift_20260620"] = advanced_reliability_result
                status["advanced_reliability_shift"] = {
                    "ok": True,
                    "version": advanced_reliability_result.get("version"),
                    "calculation_id": (advanced_reliability_result.get("identity") or {}).get("calculation_id"),
                    "settled_rows": (advanced_reliability_result.get("input_contract") or {}).get("settled_prediction_rows"),
                    "crc_status": (advanced_reliability_result.get("conformal_risk_control") or {}).get("status"),
                    "mmd_severity": (advanced_reliability_result.get("mmd") or {}).get("severity"),
                    "bbse_status": (advanced_reliability_result.get("bbse") or {}).get("status"),
                    "trust_cap_pct": advanced_reliability_result.get("trust_cap_pct"),
                    "stage": advanced_stage,
                }
            except Exception as exc:
                canonical.setdefault("metadata", {})["advanced_reliability_shift_status"] = "FAILED SAFELY"
                canonical["metadata"]["advanced_reliability_shift_error"] = str(exc)[:500]
                status["advanced_reliability_shift"] = {"ok": False, "optional": True, "message": str(exc)}
                status["errors"].append(f"Advanced reliability/shift layer: {exc}")

            # Build the history-first research evidence exactly once inside the
            # Settings transaction. It consumes only the completed H1 frame and
            # already-computed canonical outputs; protected formulas, decisions,
            # thresholds, weights and original paths are never changed.
            history_bundle = {}
            try:
                from core.history_research_pipeline_20260620 import build_history_research_transaction
                previous_published = st.session_state.get("canonical_decision_result")
                previous_published = previous_published if isinstance(previous_published, Mapping) else {}
                canonical, history_bundle, history_summary = build_history_research_transaction(
                    canonical,
                    completed_h1=final_df,
                    priority_table=canonical_priority_table,
                    settled_predictions=settled_research_predictions,
                    calibrated_bundle=upgraded_bundle if isinstance(upgraded_bundle, Mapping) else {},
                    previous=previous_published,
                )
                status["history_research_evidence"] = {
                    "ok": True,
                    "version": history_summary.get("version"),
                    "total_rows": history_summary.get("total_rows"),
                    "tables_affected": history_summary.get("tables_affected"),
                    "protected_outputs_changed": history_summary.get("protected_outputs_changed"),
                    "duration_ms": history_summary.get("duration_ms"),
                }
            except Exception as exc:
                # Fail safely: the protected canonical object remains publishable,
                # while no partial evidence table is committed.
                history_bundle = {}
                canonical.setdefault("metadata", {})["history_research_evidence_status"] = "FAILED SAFELY"
                canonical["metadata"]["history_research_evidence_error"] = str(exc)[:500]
                status["history_research_evidence"] = {"ok": False, "optional": True, "message": str(exc)}
                status["errors"].append(f"History research evidence: {exc}")

            # Regime transition, drift and trust evidence is computed once here.
            # It wraps the protected regime as a warning/calibration layer and
            # never overwrites the canonical regime or decision.
            try:
                from core.regime_transition_trust_20260621 import build_regime_transition_trust
                previous_published = st.session_state.get("canonical_decision_result")
                previous_published = previous_published if isinstance(previous_published, Mapping) else {}
                canonical, regime_trust_result, regime_trust_history_bundle = build_regime_transition_trust(
                    canonical, completed_h1=final_df, priority_table=canonical_priority_table,
                    settled_predictions=settled_research_predictions,
                    calibrated_bundle=upgraded_bundle if isinstance(upgraded_bundle, Mapping) else {},
                    previous=previous_published,
                )
                st.session_state["regime_transition_trust_center_20260621"] = regime_trust_result
                status["regime_transition_trust_center"] = {
                    "ok": True,
                    "drift_type": (regime_trust_result.get("transition_summary") or {}).get("drift_type"),
                    "transition_status": (regime_trust_result.get("transition_summary") or {}).get("transition_status"),
                    "protected_regime_unchanged": regime_trust_result.get("protected_regime_unchanged"),
                }
            except Exception as exc:
                regime_trust_history_bundle = {}
                canonical.setdefault("metadata", {})["regime_transition_trust_status"] = "FAILED SAFELY"
                canonical["metadata"]["regime_transition_trust_error"] = str(exc)[:500]
                status["regime_transition_trust_center"] = {"ok": False, "optional": True, "message": str(exc)}
                status["errors"].append(f"Regime transition trust center: {exc}")

            # Ten-paper research-validation layer. This executes once on the
            # Settings Run Calculation path, uses bounded settled evidence, and
            # publishes shadow/trust outputs only. It never creates or reverses a
            # BUY/SELL direction.
            try:
                from core.research_validation_common_20260621 import profile_int
                from core.research_validation_layer_20260621 import build_research_validation_transaction
                settled_method_predictions = (
                    trust_store.method_frame(status="SETTLED", limit=profile_int(12000, 2000))
                    if trust_store is not None else pd.DataFrame()
                )
                previous_published = st.session_state.get("canonical_decision_result")
                previous_published = previous_published if isinstance(previous_published, Mapping) else {}
                canonical, research_validation_bundle, research_validation_summary = build_research_validation_transaction(
                    canonical,
                    completed_h1=final_df,
                    settled_predictions=settled_research_predictions,
                    settled_method_predictions=settled_method_predictions,
                    preflight_validation=research_validation_preflight,
                    previous=previous_published,
                    runtime_metrics={
                        "calculation_latency_ms": (time.perf_counter() - perf_started) * 1000.0,
                        "rss_mb": (int(_process.memory_info().rss) / (1024.0 * 1024.0)) if _process is not None else None,
                    },
                )
                history_bundle.update(research_validation_bundle)
                status["research_validation_20260621"] = {"ok": True, **research_validation_summary}
            except Exception as exc:
                # Optional statistical evidence fails closed: no promotion and no
                # direction change. The protected canonical payload remains valid.
                canonical.setdefault("metadata", {})["research_validation_20260621_status"] = "FAILED SAFELY"
                canonical["metadata"]["research_validation_20260621_error"] = str(exc)[:500]
                status["research_validation_20260621"] = {"ok": False, "optional": True, "message": str(exc)}
                status["errors"].append(f"Research validation layer: {exc}")

            # Ten requested paper concepts are built exactly once here, after all
            # required settled evidence is available and immediately before the
            # canonical publication gate. Builders are intentionally absent from
            # tabs/pages/renderers. Outputs start in SHADOW mode and can only keep
            # a protected direction or conservatively recommend WAIT.
            try:
                from core.ten_paper_research_layers_20260621 import build_ten_paper_research_transaction
                from core.research_validation_store_20260621 import BUNDLE_KEY
                previous_published = st.session_state.get("canonical_decision_result")
                previous_published = previous_published if isinstance(previous_published, Mapping) else {}
                methods_for_ten_papers = (
                    settled_method_predictions
                    if "settled_method_predictions" in locals() and isinstance(settled_method_predictions, pd.DataFrame)
                    else pd.DataFrame()
                )
                canonical, ten_paper_bundle, ten_paper_summary = build_ten_paper_research_transaction(
                    canonical,
                    completed_h1=final_df,
                    settled_predictions=settled_research_predictions,
                    settled_method_predictions=methods_for_ten_papers,
                    previous=previous_published,
                )
                # Both research generations share the same custom bundle key. Merge
                # table rows instead of replacing the already-staged transaction.
                staged = history_bundle.setdefault(BUNDLE_KEY, {})
                for table_name, rows in (ten_paper_bundle.get(BUNDLE_KEY, {}) or {}).items():
                    staged.setdefault(table_name, []).extend(list(rows or []))
                status["ten_paper_research_20260621"] = {"ok": True, **ten_paper_summary}
            except Exception as exc:
                canonical.setdefault("metadata", {})["ten_paper_research_status"] = "INSUFFICIENT_EVIDENCE"
                canonical["metadata"]["ten_paper_research_error"] = str(exc)[:500]
                status["ten_paper_research_20260621"] = {
                    "ok": False, "optional": True, "mode": "SHADOW",
                    "status": "INSUFFICIENT_EVIDENCE", "message": str(exc),
                }
                status["errors"].append(f"Ten-paper shadow research layer: {exc}")

            # Consolidated ten-paper Production Promotion Guard. It executes
            # exactly once after canonical/research outputs are complete and
            # before the atomic publication gate. The guard consumes immutable
            # outputs and has no BUY/SELL reversal or WAIT-promotion authority.
            try:
                from core.production_promotion_guard_20260621 import build_production_promotion_guard_transaction
                from core.research_validation_store_20260621 import BUNDLE_KEY
                previous_published = st.session_state.get("canonical_decision_result")
                previous_published = previous_published if isinstance(previous_published, Mapping) else {}
                canonical, promotion_guard_bundle, promotion_guard_summary = build_production_promotion_guard_transaction(
                    canonical,
                    completed_h1=final_df,
                    previous=previous_published,
                    runtime_metrics={
                        "calculation_latency_ms": (time.perf_counter() - perf_started) * 1000.0,
                        "rss_mb": (int(_process.memory_info().rss) / (1024.0 * 1024.0)) if _process is not None else None,
                    },
                )
                staged = history_bundle.setdefault(BUNDLE_KEY, {})
                for table_name, rows in (promotion_guard_bundle.get(BUNDLE_KEY, {}) or {}).items():
                    staged.setdefault(table_name, []).extend(list(rows or []))
                status["production_promotion_guard_20260621"] = {"ok": True, **promotion_guard_summary}
            except Exception as exc:
                # A guard failure is visible and fail-closed. It never changes the
                # protected canonical direction and never creates partial DB rows.
                try:
                    from core.production_promotion_guard_20260621 import _fail_closed_output
                    canonical["production_promotion_guard_20260621"] = _fail_closed_output(
                        canonical, ["PROMOTION_GUARD_EXECUTION_FAILED", str(exc)[:300]]
                    )
                except Exception:
                    canonical["production_promotion_guard_20260621"] = {
                        "promotion_status": "BLOCKED_FAIL_CLOSED", "promotion_level": "BLOCKED",
                        "support_coverage": 0.0, "overlap_status": "NOT_IDENTIFIABLE",
                        "hcope_lower_bound": None, "doubly_robust_value": None,
                        "importance_weight_diagnostics": {"status": "NOT_IDENTIFIABLE"},
                        "anchor_robustness_score": None, "regime_duration_distribution": {},
                        "regime_transition_hazard": None, "var_es_joint_score": None,
                        "es_backtest_status": "INSUFFICIENT_EVIDENCE", "cvar_95": None,
                        "cvar_99": None, "cdar_95": None, "drawdown_probability_bound": None,
                        "risk_multiplier": 0.0, "confidence_adjustment": 0.0,
                        "priority_adjustment": 0.0, "wait_veto": False,
                        "blocking_reasons": ["PROMOTION_GUARD_EXECUTION_FAILED"],
                        "baseline_version": "canonical-baseline", "candidate_version": "shadow-candidate-v1",
                        "evidence_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
                    }
                status["production_promotion_guard_20260621"] = {
                    "ok": False, "status": "BLOCKED_FAIL_CLOSED", "message": str(exc),
                }
                status["errors"].append(f"Production Promotion Guard: {exc}")

            # Pre-publication invariant gate. The exact diagnostic and rejected
            # generation are persisted; the previous completed canonical state is
            # never overwritten by an invalid generation.
            from core.canonical_data_validation_20260621 import validate_canonical_payload
            prepublication_validation = validate_canonical_payload(canonical)
            status["research_prepublication_validation"] = {
                "status": prepublication_validation.status,
                "generation_id": prepublication_validation.generation_id,
                "critical_failure_count": prepublication_validation.critical_failure_count,
                "failed_constraints": prepublication_validation.failed_constraints,
            }
            if not prepublication_validation.publication_allowed:
                from core.research_validation_store_20260621 import record_rejected_generation
                previous_valid = st.session_state.get("canonical_decision_result")
                previous_valid = previous_valid if isinstance(previous_valid, Mapping) else {}
                status["research_validation_rejection"] = record_rejected_generation(
                    prepublication_validation,
                    reason="Pre-publication canonical validation rejected the generation.",
                    previous_valid=previous_valid,
                )
                status["ok"] = False
                status["errors"].append("Pre-publication validation blocked the invalid generation; previous canonical generation was preserved.")
                st.session_state["research_validation_diagnostic_20260621"] = prepublication_validation.as_dict()
                return status
            try:
                from core.research_validation_store_20260621 import BUNDLE_KEY
                custom_bundle = history_bundle.setdefault(BUNDLE_KEY, {})
                # If the optional statistical layer failed safely, still persist
                # the successful source-validation generation in the canonical
                # transaction. A successful layer already staged these rows.
                if not custom_bundle:
                    for table_name, rows in research_validation_preflight.atomic_rows(
                        source_generation_id=str(canonical.get("canonical_calculation_id") or canonical.get("run_id") or "")
                    ).items():
                        custom_bundle.setdefault(table_name, []).extend(rows)
                for table_name, rows in prepublication_validation.atomic_rows(source_generation_id=str(canonical.get("canonical_calculation_id") or canonical.get("run_id") or "")).items():
                    custom_bundle.setdefault(table_name, []).extend(rows)
            except Exception as exc:
                status["errors"].append(f"Research validation evidence staging: {exc}")

            # Additive data-quality, lineage, incremental-refresh and mobile
            # evidence. This reuses the existing preflight and pre-publication
            # authorities; it does not calculate or modify any protected output.
            try:
                from core.history_quality_store_20260621 import (
                    BUNDLE_KEY as QUALITY_BUNDLE_KEY,
                    build_quality_history_bundle,
                )
                rss_after_quality = int(_process.memory_info().rss) if _process is not None else 0
                quality_bundle, quality_summary = build_quality_history_bundle(
                    final_df, canonical, validation_report=research_validation_preflight,
                    elapsed_ms=(time.perf_counter() - perf_started) * 1000.0,
                    cpu_time_ms=(time.process_time() - cpu_started) * 1000.0,
                    rss_before_bytes=rss_before, rss_after_bytes=rss_after_quality,
                    previous_row_count=int(st.session_state.get("last_completed_h1_row_count_20260621", 0) or 0),
                )
                history_bundle[QUALITY_BUNDLE_KEY] = quality_bundle.get(QUALITY_BUNDLE_KEY, {})
                status["history_quality_mobile_20260621"] = {"ok": True, **quality_summary}
                if int(quality_summary.get("blocking_failure_count") or 0) > 0:
                    status["ok"] = False
                    status["errors"].append("Post-calculation quality contract blocked publication; previous canonical generation was preserved.")
                    st.session_state["history_quality_mobile_diagnostic_20260621"] = quality_summary
                    return status
                st.session_state["last_completed_h1_row_count_20260621"] = int(len(final_df))
            except Exception as exc:
                # Quality infrastructure is fail-closed for its own evidence but
                # may not destroy the last valid canonical result.
                status["ok"] = False
                status["history_quality_mobile_20260621"] = {"ok": False, "message": str(exc)}
                status["errors"].append(f"History quality contract: {exc}")
                return status

            # Publish only after the complete object and canonical priority table
            # validate. The previous valid run remains untouched on failure. The
            # history bundle is inserted in the same BEGIN IMMEDIATE transaction.
            adapter = publish_canonical_atomically(
                st.session_state, canonical, legacy_shared=legacy_shared,
                priority_table=canonical_priority_table,
                history_bundle=history_bundle,
            )
            # Finalize the already-staged advanced-reliability snapshot only after
            # canonical atomic publication succeeds. A failed publication leaves an
            # unreferenced STAGED row that no renderer or adapter can consume.
            if advanced_reliability_result and advanced_reliability_store is not None:
                try:
                    from core.advanced_reliability_shift_20260620 import mark_advanced_reliability_published
                    status["advanced_reliability_publication"] = mark_advanced_reliability_published(
                        str(canonical.get("canonical_calculation_id") or canonical.get("run_id") or ""),
                        advanced_reliability_store,
                    )
                except Exception as exc:
                    status["advanced_reliability_publication"] = {"ok": False, "status": "FAILED SAFELY", "reason": str(exc)}

            # Persist the compact daily feature rows only after canonical atomic
            # publication succeeds. One SQLite transaction rejects stale generations.
            try:
                from core.similar_day_intelligence_20260619 import persist_similarity_generation
                status["similar_day_persistence"] = persist_similarity_generation(
                    canonical.get("similar_day_intelligence") or {},
                    similar_day_feature_rows,
                )
            except Exception as exc:
                status["similar_day_persistence"] = {"ok": False, "status": "FAILED SAFELY", "reason": str(exc)}
                status["errors"].append(f"Similar-Day feature-store persistence: {exc}")
            try:
                from core.regime_trust_store_20260621 import persist_regime_trust_bundle
                status["regime_trust_history_persistence"] = persist_regime_trust_bundle(regime_trust_history_bundle)
            except Exception as exc:
                status["regime_trust_history_persistence"] = {"ok": False, "status": "FAILED SAFELY", "reason": str(exc)}
                status["errors"].append(f"Regime trust history persistence: {exc}")
            # Publish one read-only generation to every page/inner-tab alias.
            # This is intentionally after the canonical atomic transaction so a
            # failed run can never leave Lunch/Finder/Dinner on mixed data.
            from core.operational_sync_20260618 import synchronize_published_generation
            status["operational_sync"] = synchronize_published_generation(
                st.session_state, canonical, adapter, canonical_priority_table
            )
            ledger_write = ledger.record_result(canonical)
            status["ledger_write"] = ledger_write
            try:
                from core.trust_history_20260619 import aggregate_trust, get_trust_history_store
                trust_store = trust_store or get_trust_history_store()
                status["trust_forecast_write"] = trust_store.record_forecasts(canonical, final_df)
                latest_trust = aggregate_trust(trust_store)
                trust_store.persist_snapshot(str(canonical.get("canonical_calculation_id") or canonical.get("run_id")), latest_trust)
                st.session_state["settled_trust_summary_20260619"] = latest_trust
            except Exception as exc:
                status["trust_forecast_write"] = {"ok": False, "error": str(exc)}
                status["errors"].append(f"Trust forecast ledger: {exc}")
            if isinstance(research_result, dict) and research_result:
                try:
                    from core.research_calibration_20260618 import persist_research_result
                    status["research_persistence"] = persist_research_result(research_result)
                except Exception as exc:
                    status["research_persistence"] = {"ok": False, "status": "FAILED SAFELY", "reason": str(exc)}
            st.session_state["canonical_decision_attempt_20260617"] = {
                "run_id": canonical.get("run_id"), "calculation_status": canonical.get("calculation_status"),
                "failure_reason": None, "data_signature": canonical.get("data_signature"),
                "calculation_generation": canonical.get("calculation_generation"),
            }
            status["canonical"] = {
                "ok": True, "run_id": canonical.get("run_id"),
                "decision": (canonical.get("final_decision") or {}).get("final_decision"),
                "selected_horizon": (canonical.get("final_decision") or {}).get("selected_horizon"),
            }
            status["calibration"] = (canonical.get("reliability") or {}).get("calibration_by_horizon", {})
            status["drift"] = canonical.get("drift", {})
            status["canonical"]["calculation_generation"] = canonical.get("calculation_generation")
            status["calculation_generation"] = canonical.get("calculation_generation")
            status["run_id"] = canonical.get("run_id")
            status["canonical"]["priority_rows"] = int(len(canonical_priority_table)) if isinstance(canonical_priority_table, pd.DataFrame) else 0
            status["adapter_version"] = adapter.get("version") if isinstance(adapter, dict) else None
            # Publish the adapter details only after the canonical transaction
            # succeeds; failed attempts cannot overwrite the last valid generation.
            st.session_state["full_metric_authority_20260618"] = full_metric_authority
            st.session_state["canonical_completed_ohlc_df_20260617"] = clean_preflight
            st.session_state["last_df"] = clean_preflight
            if isinstance(st.session_state.get("dv_pp_df"), pd.DataFrame):
                st.session_state["lunch_5layer_powerbi_df"] = st.session_state["dv_pp_df"]

            # Finish the Research pack with the final canonical priority history
            # and causal evidence, then publish every existing workspace alias.
            if isinstance(research_pack, dict) and research_pack:
                research_pack["regime_nlp_history"] = canonical_priority_table
                research_pack["causal_quant_support"] = st.session_state.get("causal_quant_support_20260618", {})
                research_pack["ten_paper_research_calibration"] = st.session_state.get("research_calibration_20260618", {})
                research_pack["advanced_reliability_shift"] = st.session_state.get("advanced_reliability_shift_20260620", {})
                research_pack["canonical_calculation_id"] = canonical.get("canonical_calculation_id")
                research_pack["research_calculation_id"] = (canonical.get("research_calibration") or {}).get("canonical_calculation_id")
                st.session_state["research_pack_20260612"] = research_pack
                try:
                    import json
                    from tabs.research import _safe as _research_safe
                    st.session_state["research_export_20260612"] = json.dumps(_research_safe(research_pack), indent=2, ensure_ascii=False, default=str)
                except Exception:
                    pass
            from core.system_wide_completion_20260618 import publish_system_wide_completion
            manifest = publish_system_wide_completion(
                st.session_state,
                canonical=canonical,
                adapter=adapter,
                priority_table=canonical_priority_table,
                metric_result=status.get("metric") or {},
                regime_detail_tables=detail_tables,
                nlp_result=nlp_result,
                research_pack=research_pack,
                powerbi_status=status.get("powerbi") or {},
                errors=status.get("errors") or [],
            )
            status["readiness"] = manifest
            # Persist full historical DataFrames only after every existing
            # renderer/readiness hook has consumed the successful generation.
            # Session state keeps at most a display page; the database retains
            # the complete rows for history and export queries.
            try:
                from core.compact_canonical_20260619 import get_compact_summary
                from core.performance_store_20260619 import (
                    spool_history_frames, spool_nested_history_frames, compact_adapter_frames, session_dataframe_audit, record_timing,
                )
                summary = get_compact_summary(st.session_state)
                calc_id = str(summary.get("calculation_id") or canonical.get("canonical_calculation_id") or canonical.get("run_id"))
                status["disk_backed_history"] = spool_history_frames(
                    st.session_state, calc_id, phone_mode=bool(st.session_state.get("phone_mode", False))
                )
                status["disk_backed_nested_history"] = spool_nested_history_frames(
                    st.session_state, calc_id, phone_mode=bool(st.session_state.get("phone_mode", False))
                )
                compact_adapter_frames(st.session_state, phone_mode=bool(st.session_state.get("phone_mode", False)))
                status["session_dataframe_audit_after"] = session_dataframe_audit(st.session_state)
                record_timing(st.session_state, "run_calculation", time.perf_counter() - perf_started, calculation_id=calc_id)
            except Exception as exc:
                status["disk_backed_history"] = {"ok": False, "optional_error": str(exc)}
            if not manifest.get("ready"):
                missing = [name for name, item in (manifest.get("components") or {}).items() if not bool((item or {}).get("ready"))]
                status["ok"] = False
                status["errors"].append("Published generation is partial: " + ", ".join(missing))
        except Exception as exc:
            status["ok"] = False
            status["errors"].append(f"Canonical decision: {exc}")
            st.session_state["canonical_decision_attempt_20260617"] = {
                "calculation_status": "FAILED", "failure_reason": str(exc),
                "preserved_last_valid": bool(st.session_state.get("last_valid_canonical_decision_result_20260617")),
            }

        status["elapsed_seconds"] = round(time.time() - started, 3)
        try:
            rss_after = int(_process.memory_info().rss) if _process is not None else 0
        except Exception:
            rss_after = 0
        try:
            import resource
            raw_peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            peak_rss = raw_peak * 1024 if raw_peak < 10_000_000 else raw_peak
        except Exception:
            peak_rss = max(rss_before, rss_after)
        status["performance"] = {
            "duration_seconds": round(time.perf_counter() - perf_started, 6),
            "rss_before_bytes": rss_before, "rss_after_bytes": rss_after, "peak_rss_bytes": peak_rss,
            "measurement_scope": "server process; iPhone CPU/RAM is not observable from Streamlit server",
        }
        status["built_at"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["settings_run_status_20260617"] = status
        st.session_state["settings_run_complete_20260617"] = bool(status.get("canonical", {}).get("ok"))
        try:
            from core.operational_sync_20260618 import record_operational_error
            for message in status.get("errors", [])[-12:]:
                record_operational_error(st.session_state, "Settings Run Calculation", message, stage="calculation")
        except Exception:
            pass
        return status
    finally:
        status.setdefault("elapsed_seconds", round(time.time() - started, 3))
        status.setdefault("built_at", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
        st.session_state["settings_run_status_20260617"] = status
        st.session_state.pop("calculation_staging_ohlc_df_20260617", None)
        st.session_state[lock_key] = False
