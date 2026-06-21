import streamlit as st
from core.streamlit_compat_20260615 import install_streamlit_compat

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    def st_autorefresh(*args, **kwargs):
        return None

from core.common import init_state
from core.styles import apply_global_styles
from core.ui_relationship import init_ui_relationship_state, sync_shared_connection_signature
from core.system_contract import init_system_contract, maybe_persist_runtime_snapshot, update_data_quality_from_session
from core.app.lifecycle import _safe_run_page
from core.app.routes import load_tab
from core.app.refresh import run_deferred_refresh
from core.code_quality import run_light_maintenance
from core.pro_quality_upgrade import repair_session_contract
from core.global_upgrade import apply_extra_css, apply_dedup_metric_css
from core.pro_terminal_uiux import apply_pro_terminal_css, apply_pro_terminal_runtime_helpers, render_pro_command_center_bar, render_pro_popup_layer
from core.v6_final_ui_logic_patch import install_runtime as install_v6_runtime
from core.full_system_upgrade import apply_v21_uiux, render_popup
from core.streamlit_safe_dataframe import install_safe_dataframe_patch
from core.ui.app_polish import apply_next_level_uiux, render_real_app_header
from core.light_auth_20260612 import render_auth_gate
from core.galileo_theme_20260612 import apply_galileo_theme
from core.state_manager import init_future_safety_guard
from ui.app_shell import inject_mobile_css, render_main_menu_drawer, render_top_status_bar, render_ui_health_check
from ui.home_master_control_bar_20260615 import render_home_master_control_bar
from ui.sidebar_hard_lock import init_sidebar_policy, inject_sidebar_policy_css
from ui.sidebar_permanent_disable_20260621 import apply_permanent_sidebar_disable
from ui.liquid_glass_theme_20260615 import apply_liquid_glass_theme

from core.adx_shared_sync_20260615 import ensure_shared_calculation_result, install_phone_safety_defaults
from core.tab_state_stability_20260615 import stabilize_tab_state
from core.canonical_runtime_20260617 import begin_rerun, build_runtime_context
from ui.mobile_low_heat_20260617 import apply_mobile_low_heat_css, should_enable_full_autorefresh


def run_app():
    try:
        install_streamlit_compat()
    except Exception:
        pass

    try:
        install_safe_dataframe_patch()
    except Exception:
        pass

    try:
        from core.structured_result_display_20260617 import install_structured_result_display
        install_structured_result_display()
    except Exception:
        pass

    try:
        st.set_page_config(page_title="M1 ADX Quant Pro", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
    except Exception:
        pass

    # Disable Streamlit's automatic pages navigation and native sidebar before
    # authentication or any page renderer can create a phone-blocking drawer.
    try:
        apply_permanent_sidebar_disable()
    except Exception:
        pass

    # Authentication is intentionally evaluated before app state, shared
    # calculations, navigation or sidebar policy.  This prevents sidebar
    # controls from flashing on the login page and avoids spending phone CPU/RAM
    # on market engines before the user enters the application.
    try:
        if not render_auth_gate():
            return
    except Exception as exc:
        st.error("Login gate failed. Guest mode can still be used after fixing the auth error.")
        st.code(str(exc))
        return

    try:
        init_state()
        begin_rerun(st.session_state)
        init_future_safety_guard()
        init_sidebar_policy()
        init_system_contract()
        init_ui_relationship_state()
        try:
            install_phone_safety_defaults()
            stabilize_tab_state()
        except Exception:
            pass
    except Exception as exc:
        st.error("App state initialization failed.")
        st.code(str(exc))
        return

    # Authenticated guarded startup: server-side secrets may connect once and
    # calculate only when a newer completed H1 exists. Manual Settings Run remains
    # available, and guest sessions are always excluded.
    try:
        from core.secure_api_startup_20260619 import run_guarded_startup
        try:
            import tabs.home as _startup_home
            _startup_ns = _startup_home.__dict__
        except Exception:
            _startup_ns = {}
        run_guarded_startup(st.session_state, _startup_ns)
    except Exception as exc:
        st.session_state["secure_startup_error_20260619"] = f"{type(exc).__name__}: {exc}"

    try:
        phone_mode = bool(st.session_state.get("phone_mode", False))
        st.session_state["logic_first_mobile_20260618"] = bool(phone_mode)
        apply_global_styles(phone_mode)
        apply_extra_css()
        apply_dedup_metric_css()
        # Phone mode intentionally omits stacked decorative themes, animated
        # backgrounds and terminal overlays. Calculation/render logic is kept.
        if not phone_mode:
            apply_pro_terminal_css()
            apply_pro_terminal_runtime_helpers()
            apply_v21_uiux()
            apply_next_level_uiux()
            apply_galileo_theme()
            apply_liquid_glass_theme()
            try:
                from ui.safe_tab_switch_20260615 import inject_motion_background_css
                inject_motion_background_css()
            except Exception:
                pass
        inject_mobile_css()
        inject_sidebar_policy_css()
        apply_mobile_low_heat_css(st, phone_mode)
    except Exception as exc:
        st.warning("Styles failed to load, but the app will continue.")
        with st.expander("Show style error"):
            st.code(str(exc))

    try:
        if st.session_state.get("ws_enabled", False):
            try:
                from core.websocket_feed import consume_websocket_into_session
                consume_websocket_into_session()
            except Exception:
                pass
        nav_age = __import__("time").time() - float(st.session_state.get("ui_navigation_click_ts", 0.0) or 0.0)
        fast_nav = bool(st.session_state.get("fast_tab_switch_active", False)) or nav_age < 2.5
        if not fast_nav:
            run_deferred_refresh()
            run_light_maintenance()
            repair_session_contract()
        else:
            st.session_state["deferred_auto_refresh_reason"] = "Skipped refresh/maintenance for fast tab switch."
    except Exception as exc:
        st.warning("Auto data refresh failed. You can still use the app manually.")
        with st.expander("Show refresh error"):
            st.code(str(exc))

    try:
        update_data_quality_from_session(persist=False)
        sync_shared_connection_signature()
        maybe_persist_runtime_snapshot("app_cycle")
    except Exception:
        pass

    try:
        inject_sidebar_policy_css()
        # Native sidebar is permanently removed. The main-page Liquid Drawer is
        # the single navigation system; the legacy fallback flag is forced off.
        st.session_state["use_native_sidebar_fallback_20260619"] = False
        tab = str(st.session_state.get("active_page") or st.session_state.get("tab_choice") or "Settings")
        st.session_state["active_page"] = tab
        stabilize_tab_state()
    except Exception as exc:
        st.warning("Main-page navigation state required a safe fallback.")
        st.caption(str(exc))
        try:
            from ui.navigation_registry import normalize_active_tab
            tab = normalize_active_tab(st.session_state.get("tab_choice", st.session_state.get("active_page", "Settings")))
        except Exception:
            tab = st.session_state.get("tab_choice", "Settings") or "Settings"
        st.session_state["active_page"] = tab
        st.session_state["tab_choice"] = tab

    try:
        # Compact real-app shell: only one visible top rail stays above tabs.
        # Older bulky status/command sections are kept available inside the drawer
        # instead of being duplicated above every page.
        compact_shell = bool(st.session_state.get("compact_liquid_app_shell_20260615", True))
        drawer_open = bool(st.session_state.get("new7_main_menu_drawer_open", False) or st.session_state.get("menu_open", False))
        if not compact_shell:
            render_top_status_bar(tab)
        render_home_master_control_bar(tab)
        tab = render_main_menu_drawer(tab)
        phone_mode = bool(st.session_state.get("phone_mode", False))
        if not phone_mode:
            render_pro_popup_layer()
            render_popup()
        if ((not compact_shell) or drawer_open) and not phone_mode:
            # These are optional visual status layers only. Showing them only when
            # the drawer is open prevents duplicate app-header/button clutter.
            render_real_app_header(tab)
            render_pro_command_center_bar(tab)
        if not phone_mode:
            install_v6_runtime(tab)
        inject_sidebar_policy_css()
    except Exception:
        pass

    try:
        apply_permanent_sidebar_disable()
    except Exception:
        pass

    # Resolve navigation once, synchronize once, then pass a lightweight runtime
    # context to the selected renderer. Hidden pages and inner tabs remain idle.
    try:
        stabilize_tab_state()
        tab = str(st.session_state.get("active_page", tab) or "Settings")
        subpage = str(st.session_state.get("active_subpage", "") or "")
        ensure_shared_calculation_result(force=False)
        try:
            from core.operational_sync_20260618 import ensure_generation_consistency
            generation_sync = ensure_generation_consistency(st.session_state)
        except Exception as exc:
            generation_sync = {"ok": False, "status": "CHECK", "error": str(exc)}
        runtime_context = build_runtime_context(
            st.session_state, active_page=tab, active_subpage=subpage,
            phone_mode=bool(st.session_state.get("phone_mode", False)),
        )
        runtime_context["generation_sync"] = generation_sync
    except Exception as exc:
        try:
            from core.operational_sync_20260618 import record_operational_error
            record_operational_error(st.session_state, "Runtime synchronization", exc, stage="runtime")
        except Exception:
            pass
        runtime_context = {"active_page": tab, "active_subpage": "", "canonical_status": "DATA NOT READY", "error": str(exc)}

    try:
        if should_enable_full_autorefresh(st.session_state, tab, str(runtime_context.get("active_subpage", ""))):
            st_autorefresh(interval=600000, key="ten_min_refresh")
        else:
            st.session_state["ten_min_refresh_disabled_reason_20260617"] = "Phone low-heat mode or non-live/closed page"
    except Exception:
        pass

    show = load_tab(tab)
    _safe_run_page(tab, show, runtime_context=runtime_context)
    try:
        # Final CSS wins over any old tab-level sidebar styles.
        inject_sidebar_policy_css()
    except Exception:
        pass
    st.session_state["fast_tab_switch_active"] = False
