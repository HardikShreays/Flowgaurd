"""FlowGuard risk scoring engine. Computes delay risk from DB data."""

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from database import (
    get_delay_factors,
    get_node_by_city,
    get_route,
    get_shipment,
    log_risk_score,
)


def _get_scoring_defaults() -> dict[str, Any]:
    """Get scoring defaults from delay factors."""
    factors = get_delay_factors()
    return factors.get("scoring_defaults", {})


@dataclass
class RiskResult:
    """Result of a risk calculation for a single shipment."""

    shipment_id: str
    score: float
    level: str
    top_factors: list[dict[str, Any]]
    recommendation: str
    timestamp: str


def get_congestion_score(city_names: list[str]) -> float:
    """Get average congestion score for nodes by city. Returns 50.0 if no nodes found."""
    factors = get_delay_factors()
    score_map = factors.get("congestion_score_map", {})
    defaults = _get_scoring_defaults()
    fallback = float(defaults.get("congestion_fallback", 0.0))
    scores = []
    for city in city_names:
        node = get_node_by_city(city)
        if node and node.get("congestion_level"):
            level = node["congestion_level"].lower()
            scores.append(score_map.get(level, fallback))
    if not scores:
        return fallback
    return sum(scores) / len(scores)


def get_checkpoint_score(city_names: list[str]) -> float:
    """Get average checkpoint delay score. Normalises 8hrs=100. Returns 40.0 if no nodes."""
    defaults = _get_scoring_defaults()
    normalisation_hours = float(defaults.get("checkpoint_normalization_hours", 1.0))
    fallback = float(defaults.get("checkpoint_fallback", 0.0))
    scores = []
    for city in city_names:
        node = get_node_by_city(city)
        if node and "avg_processing_time_hours" in node:
            hrs = node["avg_processing_time_hours"] or 0
            normalised = min(100.0, (hrs / max(normalisation_hours, 1e-6)) * 100.0)
            scores.append(normalised)
    if not scores:
        return fallback
    return sum(scores) / len(scores)


def get_weather_score(route_id: str) -> float:
    """Get deterministic weather score for route. Weighted toward no impact."""
    defaults = _get_scoring_defaults()
    seed_modulo = int(defaults.get("weather_seed_modulo", 1))
    profile = defaults.get("weather_profile", [0.0])
    random.seed(hash(route_id) % max(seed_modulo, 1))
    return float(random.choice(profile))


def get_highway_risk_score(primary_highway: str) -> float:
    """Get highway risk score from delay factors. Returns 50.0 if not found."""
    factors = get_delay_factors()
    scores = factors.get("highway_risk_scores", {})
    defaults = _get_scoring_defaults()
    fallback = float(defaults.get("highway_fallback", 0.0))
    return float(scores.get(primary_highway, fallback))


def get_cargo_multiplier(cargo_type: str) -> float:
    """Get cargo priority multiplier. Returns 1.0 if not found."""
    factors = get_delay_factors()
    multipliers = factors.get("cargo_priority_multipliers", {})
    return multipliers.get(cargo_type, 1.0)


def calculate_risk(shipment_id: str) -> RiskResult:
    """Compute full risk score for a shipment. Persists to risk_history."""
    shipment = get_shipment(shipment_id)
    if not shipment:
        raise ValueError(f"Shipment {shipment_id} not found")

    route = get_route(shipment["route_id"])
    if not route:
        raise ValueError(f"Route {shipment['route_id']} not found")

    checkpoints = route.get("checkpoints") or []
    cities = list(
        dict.fromkeys(
            [shipment["origin"], shipment["destination"]] + checkpoints
        )
    )

    traffic_score = get_congestion_score(cities)
    checkpoint_score = get_checkpoint_score(cities)
    weather_score = get_weather_score(shipment["route_id"])
    highway_score = get_highway_risk_score(route["primary_highway"])
    cargo_mult = get_cargo_multiplier(shipment["cargo_type"])

    factors = get_delay_factors()
    weights = factors.get("weights", {})
    w_traffic = float(weights.get("traffic_congestion", 0.0))
    w_checkpoint = float(weights.get("checkpoint_delay", 0.0))
    w_weather = float(weights.get("weather_impact", 0.0))
    w_cargo = float(weights.get("cargo_priority", 0.0))
    w_route = float(weights.get("route_history", 0.0))

    contributions = [
        ("traffic_congestion", traffic_score * w_traffic),
        ("checkpoint_delay", checkpoint_score * w_checkpoint),
        ("weather_impact", weather_score * w_weather),
        ("cargo_priority", highway_score * w_cargo),
        ("route_history", highway_score * w_route),
    ]

    raw_score = sum(c for _, c in contributions)
    status = (shipment.get("status") or "").lower()
    eta_hours = float(shipment.get("eta_hours") or 0.0)
    defaults = _get_scoring_defaults()
    status_adjustments = defaults.get("status_adjustments", {})
    status_adjust = float(status_adjustments.get(status, 0.0))
    eta_cfg = defaults.get("eta_adjustment", {})
    eta_baseline = float(eta_cfg.get("baseline_hours", 0.0))
    eta_slope = float(eta_cfg.get("slope", 0.0))
    eta_min = float(eta_cfg.get("min", 0.0))
    eta_max = float(eta_cfg.get("max", 0.0))
    eta_adjust = min(eta_max, max(eta_min, (eta_hours - eta_baseline) * eta_slope))
    final_score = min(
        100.0,
        max(0.0, (raw_score * cargo_mult) + status_adjust + eta_adjust),
    )
    contributions.extend(
        [
            ("status_signal", status_adjust),
            ("eta_signal", eta_adjust),
        ]
    )

    thresholds = factors.get("thresholds", {})
    low_thresh = float(thresholds.get("low_risk", 0.0))
    # medium_risk is the MEDIUM->HIGH boundary; fallback keeps backward compatibility.
    medium_thresh = float(
        thresholds.get("medium_risk", thresholds.get("high_risk", 100.0))
    )

    if final_score < low_thresh:
        level = "LOW"
    elif final_score < medium_thresh:
        level = "MEDIUM"
    else:
        level = "HIGH"

    sorted_factors = sorted(contributions, key=lambda x: -x[1])[:3]
    top_factors = [
        {"name": name, "contribution": round(c, 2)} for name, c in sorted_factors
    ]

    if level == "HIGH":
        recommendation = "Immediate rerouting recommended."
    elif level == "MEDIUM":
        recommendation = "Monitor closely."
    else:
        recommendation = "On track."

    timestamp = datetime.now(timezone.utc).isoformat()
    log_risk_score(
        shipment_id,
        round(final_score, 2),
        level,
        top_factors,
    )

    return RiskResult(
        shipment_id=shipment_id,
        score=round(final_score, 2),
        level=level,
        top_factors=top_factors,
        recommendation=recommendation,
        timestamp=timestamp,
    )


def score_all_shipments() -> list[RiskResult]:
    """Score every shipment. Returns list sorted by score descending."""
    from database import get_all_shipments

    results = []
    for s in get_all_shipments():
        try:
            r = calculate_risk(s["shipment_id"])
            results.append(r)
        except Exception as e:
            import traceback

            traceback.print_exc()
            continue
    return sorted(results, key=lambda x: -x.score)


if __name__ == "__main__":
    for r in score_all_shipments():
        print(f"{r.shipment_id}: {r.score} ({r.level}) - {r.recommendation}")
        for f in r.top_factors:
            print(f"  - {f['name']}: {f['contribution']}")
        print()
