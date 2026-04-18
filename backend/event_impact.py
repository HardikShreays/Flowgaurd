"""Event impact persistence. Updates shipment status and ETA based on events."""

from ripple import RippleResult
from database import get_shipment, update_shipment

# Delay hours added by event type (trigger shipment)
DELAY_HOURS_BY_EVENT: dict[str, float] = {
    "roadblock": 4.0,
    "accident": 4.0,
    "traffic_jam": 2.0,
    "checkpoint_delay": 1.0,
    "weather": 2.0,
}


def apply_event_impact(
    trigger_shipment_id: str,
    event_type: str,
    ripple: RippleResult,
) -> None:
    """Update DB: set status to delayed and add ETA hours for trigger + affected shipments."""
    # 1. Update trigger shipment
    trigger = get_shipment(trigger_shipment_id)
    if trigger:
        delay = DELAY_HOURS_BY_EVENT.get(event_type, 2.0)
        new_eta = float(trigger.get("eta_hours") or 0) + delay
        update_shipment(
            trigger_shipment_id,
            status="delayed",
            eta_hours=round(new_eta, 2),
        )

    # 2. Update affected shipments (risk_increase >= 10)
    for a in ripple.affected_shipments:
        if a.risk_increase < 10:
            continue
        aff = get_shipment(a.shipment_id)
        if not aff:
            continue
        # Proportional delay: risk_increase 25 → ~2.5hr, 20 → ~2hr, 15 → ~1.5hr, 10 → ~1hr
        delay = a.risk_increase / 10.0
        new_eta = float(aff.get("eta_hours") or 0) + delay
        update_shipment(
            a.shipment_id,
            status="delayed",
            eta_hours=round(new_eta, 2),
        )
