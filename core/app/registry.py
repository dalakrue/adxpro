"""Central tab/module registry for flexible future upgrades.

To add a new tab later, only add one entry to TAB_REGISTRY and one name to
core.common.DEFAULT_TABS. The app shell will lazy-import the module, so one
broken tab will not crash the whole application.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TabSpec:
    name: str
    module: str
    function: str = "show"
    icon: str = "📌"
    layer: str = "tab"
    notes: str = ""


TAB_REGISTRY: Dict[str, TabSpec] = {
    "Home": TabSpec("Home", "tabs.antd_page_router_20260615", icon="🏠", layer="page", notes="Stable Ant Design home route using existing Lunch/Home logic."),
    "Lunch": TabSpec("Lunch", "tabs.antd_page_router_20260615", icon="🍱", layer="page", notes="Metric, history, PowerBI, priority, reliability, and local AI sections."),
    "Dinner": TabSpec("Dinner", "tabs.antd_page_router_20260615", icon="🌙", layer="page", notes="Regime summary, combine logic, and Dinner AI assistant."),
    "Morning": TabSpec("Morning", "tabs.antd_page_router_20260615", icon="🌅", layer="page", notes="Former Doo Prime / morning workspace."),
    "Data Visualization": TabSpec("Data Visualization", "tabs.antd_page_router_20260615", icon="📊", layer="page", notes="Existing PowerBI/Data Visualization renderer, run-gated."),
    "Research": TabSpec("Research", "tabs.antd_page_router_20260615", icon="🎓", layer="page", notes="Research/Data Mining/NLP/KNN/Greedy/Quant Structure route."),
    "AI Assistant": TabSpec("AI Assistant", "tabs.antd_page_router_20260615", icon="🤖", layer="page", notes="Local no-API AI Assistant route."),
    "Settings": TabSpec("Settings", "tabs.antd_page_router_20260615", icon="⚙️", layer="page", notes="Main-page settings and fallback controls."),
    # Backward compatibility routes kept for old session_state / imports.
    "Other": TabSpec("Other", "tabs.antd_page_router_20260615", icon="📂", layer="page", notes="Restored Engine, Train Data, Backtest, Pre Original and Profile workspace."),
    "Metric": TabSpec("Metric", "tabs.eurusd_h1_matrix", icon="📊", layer="inner", notes="EURUSD H1 decision metric inner section."),
}


def get_tab_spec(tab_name: str) -> TabSpec:
    """Return a valid tab spec, falling back to Lunch for unknown names."""
    return TAB_REGISTRY.get(str(tab_name), TAB_REGISTRY["Settings"])


def tab_icons() -> dict:
    """Small helper for navigation buttons without duplicating icon maps."""
    return {name: spec.icon for name, spec in TAB_REGISTRY.items()}
