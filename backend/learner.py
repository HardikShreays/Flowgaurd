"""FlowGuard learner. Self-improving weight adjustment from outcome feedback."""

from database import get_delay_factors, get_recent_outcomes, update_delay_factor

def analyse_recent_outcomes(limit: int = 20) -> dict:
    """Analyse recent outcomes for accuracy and error types."""
    outcomes = get_recent_outcomes(limit)
    total = len(outcomes)
    correct = sum(1 for o in outcomes if o.get("was_correct") == 1)
    false_highs = 0
    false_lows = 0
    for o in outcomes:
        pred = (o.get("predicted_level") or "").upper()
        actual = o.get("actual_outcome") or ""
        if pred == "HIGH" and actual == "on_time":
            false_highs += 1
        elif pred in ("LOW", "MEDIUM") and actual == "delayed":
            false_lows += 1
    accuracy = correct / total if total > 0 else 0.0
    return {
        "total_outcomes": total,
        "correct_predictions": correct,
        "false_highs": false_highs,
        "false_lows": false_lows,
        "accuracy": round(accuracy, 4),
    }


def adjust_weights() -> dict:
    """Adjust weights based on outcome analysis. Persists to DB."""
    analysis = analyse_recent_outcomes()
    total = analysis["total_outcomes"]
    if total < 5:
        factors = get_delay_factors()
        return {
            "old_weights": factors.get("weights", {}),
            "new_weights": factors.get("weights", {}),
            "reason": "Insufficient data",
            "outcomes_analysed": total,
        }

    false_highs = analysis["false_highs"]
    false_lows = analysis["false_lows"]
    weights = dict(get_delay_factors().get("weights", {}))
    old_weights = dict(weights)
    reason = ""

    diff = false_highs - false_lows
    if diff > 1:
        weights["traffic_congestion"] = weights.get("traffic_congestion", 0.3) - 0.02
        weights["checkpoint_delay"] = weights.get("checkpoint_delay", 0.25) - 0.02
        weights["route_history"] = weights.get("route_history", 0.1) + 0.02
        weights["weather_impact"] = weights.get("weather_impact", 0.2) + 0.02
        reason = "Reduced traffic/checkpoint weights; increased route_history/weather (false highs > false lows)"
    elif diff < -1:
        weights["traffic_congestion"] = weights.get("traffic_congestion", 0.3) + 0.02
        weights["checkpoint_delay"] = weights.get("checkpoint_delay", 0.25) + 0.02
        weights["route_history"] = weights.get("route_history", 0.1) - 0.02
        weights["weather_impact"] = weights.get("weather_impact", 0.2) - 0.02
        reason = "Increased traffic/checkpoint weights; reduced route_history/weather (false lows > false highs)"
    else:
        reason = "No change; predictions balanced"

    total_w = sum(weights.values())
    if total_w > 0:
        for k in weights:
            weights[k] = round(weights[k] / total_w, 4)
        adj = 1.0 - sum(weights.values())
        last_key = list(weights.keys())[-1]
        weights[last_key] = round(weights[last_key] + adj, 4)

    update_delay_factor("weights", weights)
    return {
        "old_weights": old_weights,
        "new_weights": weights,
        "reason": reason,
        "outcomes_analysed": total,
    }


if __name__ == "__main__":
    result = adjust_weights()
    print("Adjust weights result:")
    print(f"  Reason: {result['reason']}")
    print(f"  Outcomes analysed: {result['outcomes_analysed']}")
    print("  New weights:", result["new_weights"])
