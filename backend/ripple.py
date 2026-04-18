"""FlowGuard ripple impact detection. Finds cascade effects across shipment network."""

from dataclasses import dataclass

from database import get_all_shipments, get_route, get_shipment
from scoring import calculate_risk

BOOST_BY_EVENT: dict[str, int] = {
    "roadblock": 25,
    "traffic_jam": 20,
    "checkpoint_delay": 15,
    "weather": 10,
}


@dataclass
class AffectedShipment:
    """One shipment affected by a trigger event."""

    shipment_id: str
    original_risk: float
    new_risk: float
    risk_increase: float
    shared_element: str


@dataclass
class RippleResult:
    """Result of cascade impact analysis."""

    trigger_shipment_id: str
    trigger_event_type: str
    affected_shipments: list[AffectedShipment]
    affected_count: int
    max_risk_increase: float
    summary: str


def find_affected_shipments(
    trigger_shipment_id: str,
    event_type: str,
    highway: str | None = None,
) -> RippleResult:
    """Find shipments affected by a trigger event. Returns RippleResult."""
    trigger = get_shipment(trigger_shipment_id)
    if not trigger:
        raise ValueError(f"Shipment {trigger_shipment_id} not found")

    trigger_route = get_route(trigger["route_id"])
    if not trigger_route:
        raise ValueError(f"Route {trigger['route_id']} not found")

    hw = highway or trigger_route.get("primary_highway", "")
    trigger_checkpoints = set(trigger_route.get("checkpoints") or [])
    trigger_od = {trigger["origin"], trigger["destination"]}

    boost = BOOST_BY_EVENT.get(event_type, 10)

    affected: list[AffectedShipment] = []
    all_shipments = get_all_shipments()

    for s in all_shipments:
        if s["shipment_id"] == trigger_shipment_id:
            continue

        other_route = get_route(s["route_id"])
        if not other_route:
            continue

        shared_element = ""
        if other_route.get("primary_highway") == hw and hw:
            shared_element = f"{hw}"
        elif trigger_checkpoints & set(other_route.get("checkpoints") or []):
            shared_element = "checkpoint"
        elif {s["origin"], s["destination"]} & trigger_od:
            shared = {s["origin"], s["destination"]} & trigger_od
            shared_element = f"{', '.join(shared)} node"
        else:
            continue

        try:
            risk_result = calculate_risk(s["shipment_id"])
            orig = risk_result.score
        except Exception:
            continue

        new_risk = min(100.0, orig + boost)
        increase = new_risk - orig
        if increase >= 10:
            affected.append(
                AffectedShipment(
                    shipment_id=s["shipment_id"],
                    original_risk=round(orig, 2),
                    new_risk=round(new_risk, 2),
                    risk_increase=round(increase, 2),
                    shared_element=shared_element,
                )
            )

    max_inc = max((a.risk_increase for a in affected), default=0.0)
    count = len(affected)

    if hw and count > 0:
        summary = f"{event_type.replace('_', ' ').title()} on {hw} impacts {count} shipment(s) sharing the same highway."
    elif count > 0:
        summary = f"{event_type.replace('_', ' ').title()} impacts {count} shipment(s) sharing route elements."
    else:
        summary = f"No other shipments significantly affected by {event_type}."

    return RippleResult(
        trigger_shipment_id=trigger_shipment_id,
        trigger_event_type=event_type,
        affected_shipments=affected,
        affected_count=count,
        max_risk_increase=round(max_inc, 2),
        summary=summary,
    )


if __name__ == "__main__":
    from database import get_all_shipments

    first = get_all_shipments()[0]["shipment_id"]
    result = find_affected_shipments(first, "roadblock")
    print(f"Trigger: {result.trigger_shipment_id}, event: {result.trigger_event_type}")
    print(f"Affected: {result.affected_count}, max risk increase: {result.max_risk_increase}")
    print(result.summary)
    for a in result.affected_shipments:
        print(f"  - {a.shipment_id}: {a.original_risk} -> {a.new_risk} ({a.shared_element})")
