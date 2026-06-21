"""Display-only bounded risk plan; never changes canonical direction."""
from __future__ import annotations
from typing import Any, Mapping


def _number(value: Any, default: float = 0.0) -> float:
    try: return float(value)
    except Exception: return default


def build_risk_plan(state: Mapping[str, Any], canonical: Mapping[str, Any]) -> dict[str, Any]:
    balance = max(0.0, _number(state.get("account_balance") or state.get("balance"), 0.0))
    risk_pct = min(2.0, max(0.0, _number(state.get("risk_pct") or state.get("risk_percent"), 0.5)))
    stop_pips = max(1.0, _number(state.get("stop_loss_pips") or 20.0, 20.0))
    risk_amount = balance * risk_pct / 100.0
    # EURUSD standard-lot pip value proxy is explicitly labelled; it is a sizing
    # display guardrail, not a broker execution or trading formula.
    lots = max(0.0, min(10.0, risk_amount / (stop_pips * 10.0))) if balance else 0.0
    final = canonical.get("final_decision") if isinstance(canonical.get("final_decision"), Mapping) else {}
    decision = str(final.get("tradeability_decision") or final.get("final_decision") or "WAIT").upper()
    if decision not in {"BUY", "SELL"}: lots = 0.0
    return {
        "status": "READY" if lots > 0 else "BLOCK",
        "recommended_lots": round(lots, 3),
        "risk_amount": round(risk_amount, 2),
        "risk_pct": risk_pct,
        "stop_loss_pips": stop_pips,
        "decision_reference": decision,
        "display_only": True,
        "reason": "No actionable canonical direction or account inputs unavailable." if lots <= 0 else "Bounded display-only sizing guardrail.",
    }
