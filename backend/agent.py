"""FlowGuard LangGraph ReAct agent. Privacy-preserving decision reasoning."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from database import get_route, get_shipment, log_driver_event
from event_impact import apply_event_impact
from ripple import find_affected_shipments, RippleResult
from scoring import calculate_risk
from simulation import simulate_routes

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")

llm = None
agent = None


def _ensure_agent() -> None:
    """Initialise LLM and agent. Raises if API key missing."""
    global llm, agent
    if agent is not None:
        return
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not set. Add it to .env or set the environment variable."
        )
    llm = ChatGoogleGenerativeAI(
        model=GOOGLE_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
    )
    tools = [get_shipment_risk, simulate_shipment_routes, get_ripple_impact]
    agent = create_react_agent(llm, tools)


def anonymise_context(
    risk: Any, simulation: Any, ripple: Any
) -> str:
    """Build anonymised context string. No shipment IDs, cities, highways."""
    factors_str = ", ".join(
        f"{f['name']} ({f['contribution']})" for f in risk.top_factors[:3]
    )
    return f"""Logistics risk analysis context:
- Risk score: {risk.score:.1f}/100 (Level: {risk.level})
- Top delay factors: {factors_str}
- Current route: estimated {simulation.route_a_hours}hr, toll ₹{simulation.route_a_toll}
- Alternative route: {simulation.risk_delta:+.1f} risk change, {simulation.time_delta_hours:+.1f}hr, cost change ₹{simulation.cost_delta_inr}
- Cascading impact: {ripple.affected_count} other shipments affected
- Recommendation basis: {simulation.reason}

Based only on this data, provide a clear 2-sentence operational recommendation."""


@tool
def get_shipment_risk(shipment_id: str) -> str:
    """Get risk score and top factors for a shipment. Returns anonymised string."""
    r = calculate_risk(shipment_id)
    factors_str = ", ".join(
        f"{f['name']}: {f['contribution']}" for f in r.top_factors[:3]
    )
    return f"Score {r.score:.1f}/100, Level {r.level}. Top factors: {factors_str}."


@tool
def simulate_shipment_routes(shipment_id: str, event_type: str = "") -> str:
    """Compare current vs alternative route. Optional event_type makes deltas event-aware."""
    normalized_event_type = event_type.strip().lower().replace(" ", "_") if event_type else None
    s = simulate_routes(shipment_id, event_type=normalized_event_type)
    return (
        f"Risk delta {s.risk_delta:+.1f}, time delta {s.time_delta_hours:+.1f}hr, "
        f"cost delta ₹{s.cost_delta_inr:+.0f}. "
        f"Event trace: event={s.applied_event_type or 'none'}, "
        f"delay_applied={s.applied_delay_hours:+.1f}hr, "
        f"risk_boost_applied={s.applied_risk_boost:+.1f}. "
        f"Recommendation: {s.recommendation}. {s.reason}"
    )


@tool
def get_ripple_impact(shipment_id: str, event_type: str) -> str:
    """Get cascade impact for a shipment and event type."""
    r = find_affected_shipments(shipment_id, event_type)
    return (
        f"{r.affected_count} shipments affected, max risk increase {r.max_risk_increase:.1f}. "
        f"{r.summary}"
    )


def run_agent(shipment_id: str, event_description: str) -> tuple[str, RippleResult]:
    """Run ReAct agent and return (recommendation, ripple_result)."""
    _ensure_agent()
    shipment = get_shipment(shipment_id)
    if not shipment:
        raise ValueError(f"Shipment {shipment_id} not found")

    route = get_route(shipment["route_id"])
    highway = route.get("primary_highway", "") if route else ""
    desc_lower = event_description.lower()
    event_type = "roadblock"
    event_aliases = {
        "roadblock": ["roadblock", "road block"],
        "accident": ["accident", "crash", "collision"],
        "traffic_jam": ["traffic_jam", "traffic jam", "jam"],
        "checkpoint_delay": ["checkpoint_delay", "checkpoint delay", "checkpoint"],
        "weather": ["weather", "rain", "storm", "fog"],
    }
    for canonical, aliases in event_aliases.items():
        if any(alias in desc_lower for alias in aliases):
            event_type = canonical
            break

    log_driver_event(
        shipment_id=shipment_id,
        event_type=event_type,
        location=event_description[:200],
        severity="medium",
        highway=highway,
    )

    ripple = find_affected_shipments(shipment_id, event_type)
    # Apply event first so recommendation facts use latest state.
    apply_event_impact(shipment_id, event_type, ripple)
    risk = calculate_risk(shipment_id)
    simulation = simulate_routes(shipment_id, event_type=event_type)

    prompt = anonymise_context(risk, simulation, ripple)

    config = {"configurable": {}}
    recommendation = "No recommendation generated."
    try:
        result = agent.invoke({"messages": [("user", prompt)]}, config)
        messages = result.get("messages", [])
        for m in reversed(messages):
            if hasattr(m, "content") and m.content and isinstance(m.content, str):
                recommendation = m.content.strip()
                break
    except Exception:
        # Fallback keeps API available even if external LLM endpoint is unavailable.
        recommendation = (
            f"Fallback recommendation: prefer route {simulation.recommendation}. "
            f"Risk {risk.score:.1f}/100 ({risk.level}), "
            f"route delta risk {simulation.risk_delta:+.1f}, "
            f"time {simulation.time_delta_hours:+.1f}hr, cost ₹{simulation.cost_delta_inr:+.0f}, "
            f"ripple impact {ripple.affected_count} shipment(s)."
        )

    return recommendation, ripple


if __name__ == "__main__":
    try:
        _ensure_agent()
        from database import get_all_shipments

        first = get_all_shipments()[0]["shipment_id"]
        rec, ripple = run_agent(first, "roadblock reported on primary highway")
        print("Recommendation:", rec)
        print("Affected:", [a.shipment_id for a in ripple.affected_shipments])
    except Exception as e:
        print(f"Agent error: {e}")
