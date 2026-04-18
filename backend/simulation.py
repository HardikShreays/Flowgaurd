"""FlowGuard route simulation. Compares current vs alternative route."""

from dataclasses import dataclass

from database import get_route, get_shipment
from scoring import calculate_risk, get_highway_risk_score

EVENT_DELAY_HOURS: dict[str, float] = {
    "roadblock": 4.0,
    "accident": 4.0,
    "traffic_jam": 2.0,
    "checkpoint_delay": 1.0,
    "weather": 2.0,
}

EVENT_RISK_BOOST: dict[str, float] = {
    "roadblock": 25.0,
    "accident": 25.0,
    "traffic_jam": 20.0,
    "checkpoint_delay": 15.0,
    "weather": 10.0,
}


@dataclass
class SimResult:
    """Result of route simulation comparing route A (current) vs route B (alternative)."""

    shipment_id: str
    route_a_id: str
    route_a_risk: float
    route_a_distance_km: float
    route_a_hours: float
    route_a_toll: float
    route_b_id: str
    route_b_risk: float
    route_b_distance_km: float
    route_b_hours: float
    route_b_toll: float
    cost_delta_inr: float
    time_delta_hours: float
    risk_delta: float
    applied_event_type: str | None
    applied_delay_hours: float
    applied_risk_boost: float
    recommendation: str
    reason: str


def simulate_routes(shipment_id: str, event_type: str | None = None) -> SimResult:
    """Compare current route vs alternative. Event-aware when event_type is provided."""
    shipment = get_shipment(shipment_id)
    if not shipment:
        raise ValueError(f"Shipment {shipment_id} not found")

    route_a = get_route(shipment["route_id"])
    if not route_a:
        raise ValueError(f"Route {shipment['route_id']} not found")

    alt_id = route_a.get("alternative_route_id")
    if not alt_id:
        raise ValueError("No alternative route available")

    route_b = get_route(alt_id)
    if not route_b:
        raise ValueError(f"Alternative route {alt_id} not found")

    risk_result = calculate_risk(shipment_id)
    route_a_risk = risk_result.score
    applied_event_type = event_type if event_type else None
    applied_risk_boost = EVENT_RISK_BOOST.get(event_type, 0.0) if event_type else 0.0
    if event_type:
        route_a_risk = min(100.0, route_a_risk + applied_risk_boost)

    hw_a = get_highway_risk_score(route_a["primary_highway"])
    hw_b = get_highway_risk_score(route_b["primary_highway"])
    ratio = hw_b / hw_a if hw_a > 0 else 1.0
    route_b_risk = min(100.0, route_a_risk * ratio)

    route_a_hours = float(route_a.get("estimated_hours") or 0)
    applied_delay_hours = EVENT_DELAY_HOURS.get(event_type, 0.0) if event_type else 0.0
    if event_type:
        route_a_hours += applied_delay_hours
    route_a_distance_km = float(route_a.get("distance_km") or 0)
    route_a_toll = float(route_a.get("toll_cost_inr") or 0)
    route_b_hours = float(route_b.get("estimated_hours") or 0)
    route_b_distance_km = float(route_b.get("distance_km") or 0)
    route_b_toll = float(route_b.get("toll_cost_inr") or 0)

    cost_delta_inr = route_b_toll - route_a_toll
    time_delta_hours = route_b_hours - route_a_hours
    risk_delta = route_b_risk - route_a_risk

    if route_b_risk < route_a_risk - 10 and time_delta_hours < 6:
        recommendation = "B"
        pct = abs(risk_delta / route_a_risk * 100) if route_a_risk > 0 else 0
        reason = f"Route B reduces risk by {pct:.0f}% with only {time_delta_hours:.1f}hr extra travel time."
    else:
        recommendation = "A"
        reason = "Route A is preferable; alternative adds significant time or does not reduce risk enough."

    return SimResult(
        shipment_id=shipment_id,
        route_a_id=route_a["route_id"],
        route_a_risk=round(route_a_risk, 2),
        route_a_distance_km=round(route_a_distance_km, 2),
        route_a_hours=round(route_a_hours, 2),
        route_a_toll=round(route_a_toll, 2),
        route_b_id=route_b["route_id"],
        route_b_risk=round(route_b_risk, 2),
        route_b_distance_km=round(route_b_distance_km, 2),
        route_b_hours=round(route_b_hours, 2),
        route_b_toll=round(route_b_toll, 2),
        cost_delta_inr=round(cost_delta_inr, 2),
        time_delta_hours=round(time_delta_hours, 2),
        risk_delta=round(risk_delta, 2),
        applied_event_type=applied_event_type,
        applied_delay_hours=round(applied_delay_hours, 2),
        applied_risk_boost=round(applied_risk_boost, 2),
        recommendation=recommendation,
        reason=reason,
    )


if __name__ == "__main__":
    from database import get_all_shipments

    first = get_all_shipments()[0]["shipment_id"]
    sim = simulate_routes(first)
    print(f"Shipment: {sim.shipment_id}")
    print(f"Route A: {sim.route_a_id} - risk {sim.route_a_risk}, {sim.route_a_hours}hr, ₹{sim.route_a_toll}")
    print(f"Route B: {sim.route_b_id} - risk {sim.route_b_risk}, {sim.route_b_hours}hr, ₹{sim.route_b_toll}")
    print(f"Deltas: risk {sim.risk_delta:+.2f}, time {sim.time_delta_hours:+.2f}hr, cost ₹{sim.cost_delta_inr:+.2f}")
    print(f"Recommendation: {sim.recommendation} - {sim.reason}")
