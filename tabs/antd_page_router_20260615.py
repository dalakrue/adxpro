"""Top-level page router for Ant Design navigation (2026-06-15).

Routes display pages to the existing renderers without changing formulas,
calculation functions, cached data, ML tables, PowerBI logic, or copy/export
builders.
"""
from __future__ import annotations

import streamlit as st


def _safe_rerun() -> None:
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def _home_module():
    import tabs.home as home
    return home


def _home_ns() -> dict:
    return _home_module().__dict__


def _prev_data(ns: dict):
    return ns.get("_render_lunch_data_visualization_inner_tab")


def _prev_morning(ns: dict):
    return ns.get("_render_doo_prime_inner_tab")


def _copy_button(label: str, text: str, key: str) -> None:
    try:
        from streamlit_copy_button import copy_button
        copy_button(str(text), label, key=key)
    except Exception:
        st.text_area(label, str(text), height=180, key=key + "_fallback")


def _render_home_or_lunch(ns: dict) -> None:
    # True-gated canonical Lunch renderer. It reads the last committed generation
    # and never starts Settings calculation from a render interaction.
    try:
        from ui.lunch_four_core_fields_20260619 import render_lunch_six_core_fields
        render_lunch_six_core_fields()
    except Exception:
        home = _home_module()
        home.show()


def _render_lunch_subpage(ns: dict, subpage: str) -> None:
    import tabs.dinner_morning_data_patch_20260614 as dinner
    import tabs.final_three_center_upgrade_20260614 as three

    if not subpage:
        _render_home_or_lunch(ns)
        return

    st.markdown(f"### 🍱 Lunch — {subpage}")
    if subpage == "Full Metric Details + History":
        three._render_metric_detail_section(ns)
        return
    if subpage == "PowerBI Projection":
        # Cached red path is light. The original full renderer stays run/load gated.
        dinner._render_lunch_red_prediction_line()
        with st.expander("📈 Open / Close — Original Synced PowerBI Price Projection + Actual vs Error", expanded=False):
            st.caption("Original PowerBI/Data Visualization renderer is preserved. Press the button to load it; nothing heavy auto-runs on page open.")
            if st.button("▶ Load Original PowerBI Projection", key="load_original_powerbi_from_antd_lunch_20260615", use_container_width=True):
                st.session_state["load_original_powerbi_from_antd_lunch_20260615"] = True
            if st.session_state.get("load_original_powerbi_from_antd_lunch_20260615", False):
                prev = _prev_data(ns)
                if callable(prev):
                    prev()
                else:
                    st.info("Original PowerBI renderer is not available in this ZIP.")
        return
    if subpage == "Priority + Decision + Reliability":
        dinner._render_priority_decision_reliability(ns)
        try:
            rcc = ns.get("render_reliability_control_center_20260614")
            if callable(rcc):
                rcc()
        except Exception as exc:
            st.warning(f"Reliability center skipped safely: {exc}")
        return
    if subpage == "AI Assistant":
        _render_ai_assistant()
        return
    _render_home_or_lunch(ns)


def _render_dinner_page(ns: dict, subpage: str) -> None:
    import tabs.dinner_morning_data_patch_20260614 as dinner
    import tabs.final_three_center_upgrade_20260614 as three
    prev = _prev_data(ns)

    st.markdown("### 🌙 Dinner — Regime + Synced Intelligence Center")
    if not subpage:
        dinner._render_dinner(ns, prev)
        return
    if subpage == "Regime Summary":
        three._render_regime_intelligence_center(ns)
        return
    if subpage == "Combine Logic":
        dinner._render_powerbi_regime_projection(ns)
        dinner._render_priority_decision_reliability(ns)
        dinner._render_final_synced_intelligence(ns, prev)
        dinner._render_original_data_last(ns, prev)
        return
    if subpage == "AI Assistant":
        dinner._render_chatgpt_style_ai()
        return
    dinner._render_dinner(ns, prev)


def _render_morning_page(ns: dict) -> None:
    st.markdown("### 🌅 Morning — Doo Prime")
    st.caption("Former Doo Prime/Morning workspace. Existing source renderer is unchanged.")
    prev = _prev_morning(ns)
    if callable(prev):
        prev()
    else:
        st.info("Morning / Doo Prime source is not available in this ZIP.")


def _render_data_visualization(ns: dict) -> None:
    st.markdown("### 📊 Data Visualization — PowerBI Projection")
    st.caption("Uses the existing Data Visualization/PowerBI renderer only after you press Run/Load, so the app does not auto-run heavy work on start.")
    c1, c2 = st.columns(2)
    if c1.button("▶ Run / Load Data Visualization", key="run_data_visualization_antd_20260615", use_container_width=True):
        st.session_state["run_data_visualization_antd_20260615"] = True
        st.session_state["metric_run_calculate"] = True
    if c2.button("⏸ Stop / Keep Cached Only", key="stop_data_visualization_antd_20260615", use_container_width=True):
        st.session_state["run_data_visualization_antd_20260615"] = False
    prev = _prev_data(ns)
    if st.session_state.get("run_data_visualization_antd_20260615", False):
        if callable(prev):
            prev()
        else:
            st.warning("Data Visualization renderer is not available in this ZIP.")
    else:
        try:
            import tabs.dinner_morning_data_patch_20260614 as dinner
            dinner._render_lunch_red_prediction_line()
        except Exception:
            pass
        st.info("Press Run / Load Data Visualization to open the complete original renderer. Cached light preview remains available when possible.")


def _render_research_page(subpage: str) -> None:
    st.markdown("### 🎓 Research")
    if not subpage or subpage in {"Data Mining", "NLP"}:
        try:
            import tabs.research as research
            if subpage in {"Data Mining", "NLP"}:
                st.session_state["research_inner_tab"] = subpage
            research.show()
        except Exception as exc:
            st.error("Research tab could not load safely.")
            st.exception(exc)
        return

    if subpage == "KNN / Greedy":
        st.caption("Display-only mirror of existing KNN/Greedy priority outputs. No new model or prediction engine is added.")
        found = False
        for key in [
            "three_center_priority_sorted_20260614",
            "reliability_dynamic_priority_table_20260614",
            "final_synced_research_merge_pack_20260612",
            "final_merged_intelligence_pack_20260612",
        ]:
            obj = st.session_state.get(key)
            if isinstance(obj, dict):
                obj = obj.get("priority_1_to_14") or obj.get("knn_greedy_priority")
            try:
                import pandas as pd
                if isinstance(obj, pd.DataFrame) and not obj.empty:
                    st.dataframe(obj, use_container_width=True, hide_index=True, height=420)
                    _copy_button("📋 Copy KNN / Greedy Table", obj.head(120).to_csv(index=False), "copy_knn_greedy_antd_20260615")
                    found = True
                    break
            except Exception:
                pass
        if not found:
            st.info("Run Lunch/Dinner/Data Visualization once to populate the existing KNN/Greedy priority table.")
        return

    if subpage == "Quant Structure":
        st.caption("Display-only route to the existing Quant Structure intelligence/cached output.")
        try:
            import tabs.dv_quant_structure_intelligence_20260612 as quant
            renderer = getattr(quant, "_render_quant_structure_section", None)
            if callable(renderer):
                renderer("Research")
                return
        except Exception as exc:
            st.warning(f"Quant Structure renderer skipped safely: {exc}")
        pack = st.session_state.get("final_synced_research_merge_pack_20260612") or st.session_state.get("final_merged_intelligence_pack_20260612") or {}
        if isinstance(pack, dict) and pack.get("quant_structure"):
            st.json(pack.get("quant_structure"))
            _copy_button("📋 Copy Quant Structure", pack.get("quant_structure"), "copy_quant_structure_antd_20260615")
        else:
            st.info("Run Data Visualization / Final Synced Intelligence first to populate Quant Structure cache.")
        return

    try:
        import tabs.research as research
        research.show()
    except Exception as exc:
        st.error("Research tab could not load safely.")
        st.exception(exc)


def _render_ai_assistant() -> None:
    st.markdown("### 🤖 AI Assistant")
    st.caption("Local AI Assistant only. No external API and no heavy model.")
    try:
        from tabs.ai_assistant_lite import render_ai_assistant_lite_tab
        render_ai_assistant_lite_tab()
    except Exception as exc:
        st.error("AI Assistant could not load safely.")
        st.exception(exc)


def _render_settings() -> None:
    st.markdown("### ⚙️ Settings — Main-Page Sidebar Replacement")
    st.caption("Navigation, timer, API connection status, symbol/timeframe, mobile mode, run controls, and UI reset live in the main-page menu. Native sidebar is backup only.")
    c1, c2 = st.columns(2)
    if c1.button("▶ Run Calculation", key="settings_run_calc_20260615", use_container_width=True):
        st.session_state["metric_run_calculate"] = True
        st.session_state["research_run_calculate"] = True
        st.session_state["ui_navigation_click_ts"] = __import__("time").time()
        _safe_rerun()
    if c2.button("🔄 Reset UI State", key="settings_reset_ui_20260615", use_container_width=True):
        for key in ["active_subpage", "lunch_active_subpage", "dinner_active_subpage", "research_active_subpage", "new7_main_menu_drawer_open", "menu_open"]:
            st.session_state[key] = "" if "subpage" in key else False
        st.session_state["active_page"] = "Home"
        st.session_state["tab_choice"] = "Home"
        st.session_state["home_inner_tab"] = "Lunch"
        _safe_rerun()
    try:
        from ui.sidebar_fallback_panel import render_sidebar_fallback_panel
        render_sidebar_fallback_panel(expanded=True)
    except Exception as exc:
        st.warning(f"Settings controls failed safely: {exc}")


def show() -> None:
    try:
        from ui.antd_navigation_20260615 import sync_active_page_to_legacy_state
        page, subpage = sync_active_page_to_legacy_state()
    except Exception:
        page = st.session_state.get("active_page", st.session_state.get("tab_choice", "Home"))
        subpage = st.session_state.get("active_subpage", "")

    ns = _home_ns()
    if page == "Home":
        _render_home_or_lunch(ns)
    elif page == "Lunch":
        _render_lunch_subpage(ns, subpage)
    elif page == "Dinner":
        _render_dinner_page(ns, subpage)
    elif page == "Morning":
        _render_morning_page(ns)
    elif page == "Data Visualization":
        _render_data_visualization(ns)
    elif page == "Research":
        _render_research_page(subpage)
    elif page == "AI Assistant":
        _render_ai_assistant()
    elif page == "Settings":
        _render_settings()
    else:
        _render_home_or_lunch(ns)
