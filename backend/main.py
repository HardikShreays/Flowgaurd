"""FlowGuard FastAPI application. Logistics control tower API."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    get_shipment,
    init_db,
    log_driver_event,
    log_outcome,
    update_shipment,
)
from event_impact import apply_event_impact
from learner import adjust_weights
from ripple import find_affected_shipments
from scoring import calculate_risk
from simulation import simulate_routes

try:
    from agent import run_agent

    _agent_error: str | None = None
except Exception as e:
    run_agent = None
    _agent_error = str(e)


app = FastAPI(title="FlowGuard API")
allowed_origins = os.getenv("ALLOW_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in allowed_origins.split(",") if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EventRequest(BaseModel):
    """Request body for logging a driver event."""

    shipment_id: str
    event_type: str
    location: str
    severity: str
    highway: str


class OutcomeRequest(BaseModel):
    """Request body for logging an outcome."""

    shipment_id: str
    predicted_level: str
    predicted_score: float
    actual_outcome: str


class AgentRequest(BaseModel):
    """Request body for agent analysis."""

    shipment_id: str
    event_description: str


def _debug_log(location: str, message: str, data: dict, hypothesis_id: str) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": "8af04b",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        Path("/Users/hardik/Logicore-Predictive logistic Engine/.cursor/debug-8af04b.log").parent.mkdir(parents=True, exist_ok=True)
        with Path("/Users/hardik/Logicore-Predictive logistic Engine/.cursor/debug-8af04b.log").open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # #endregion


def _round_floats(obj: dict) -> dict:
    """Round float values to 2 decimal places in a dict."""
    result = {}
    for k, v in obj.items():
        if isinstance(v, float):
            result[k] = round(v, 2)
        elif isinstance(v, dict):
            result[k] = _round_floats(v)
        elif isinstance(v, list):
            result[k] = [
                _round_floats(x) if isinstance(x, dict) else x for x in v
            ]
        else:
            result[k] = v
    return result


@app.on_event("startup")
def startup() -> None:
    """Ensure database tables exist on startup."""
    init_db()


@app.get("/")
def root() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "FlowGuard API"}


@app.get("/shipments")
def list_shipments() -> list[dict]:
    """Get risk scores for all shipments. Includes status and eta_hours from DB."""
    try:
        from database import get_shipment
        from scoring import score_all_shipments

        results = score_all_shipments()
        out = []
        for r in results:
            d = _round_floats(asdict(r))
            shipment = get_shipment(r.shipment_id)
            if shipment:
                d["status"] = shipment.get("status", "")
                d["eta_hours"] = round(float(shipment.get("eta_hours") or 0), 2)
            try:
                sim = simulate_routes(r.shipment_id)
                d["recommended_route"] = sim.recommendation
                d["route_a_risk"] = round(sim.route_a_risk, 2)
                d["route_b_risk"] = round(sim.route_b_risk, 2)
                d["recommended_route_risk"] = round(
                    sim.route_a_risk if sim.recommendation == "A" else sim.route_b_risk,
                    2,
                )
            except Exception:
                # Keep /shipments resilient even when alternative route data is unavailable.
                d["recommended_route"] = None
                d["recommended_route_risk"] = None
            out.append(d)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shipments/{shipment_id}")
def get_shipment_risk(shipment_id: str) -> dict:
    """Get risk score for one shipment. Includes status and eta_hours from DB."""
    try:
        from database import get_shipment

        r = calculate_risk(shipment_id)
        d = _round_floats(asdict(r))
        shipment = get_shipment(shipment_id)
        if shipment:
            d["status"] = shipment.get("status", "")
            d["eta_hours"] = round(float(shipment.get("eta_hours") or 0), 2)
        return d
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decide/{shipment_id}")
def decide_route(shipment_id: str) -> dict:
    """Get route simulation for one shipment."""
    try:
        sim = simulate_routes(shipment_id)
        return _round_floats(asdict(sim))
    except ValueError as e:
        msg = str(e)
        if "alternative" in msg.lower():
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=404, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event")
def post_event(req: EventRequest) -> dict:
    """Log driver event and return ripple impact."""
    try:
        before = get_shipment(req.shipment_id)
        _debug_log(
            "main.py:post_event:before_apply",
            "Received event request in backend",
            {
                "shipmentId": req.shipment_id,
                "eventType": req.event_type,
                "highway": req.highway,
                "statusBefore": before.get("status") if before else None,
                "etaBefore": before.get("eta_hours") if before else None,
            },
            "H4",
        )
        log_driver_event(
            shipment_id=req.shipment_id,
            event_type=req.event_type,
            location=req.location,
            severity=req.severity,
            highway=req.highway,
        )
        ripple = find_affected_shipments(
            req.shipment_id, req.event_type, req.highway or None
        )
        apply_event_impact(req.shipment_id, req.event_type, ripple)
        after = get_shipment(req.shipment_id)
        risk_after = calculate_risk(req.shipment_id)
        _debug_log(
            "main.py:post_event:after_apply",
            "Applied event impact and recomputed risk",
            {
                "shipmentId": req.shipment_id,
                "statusAfter": after.get("status") if after else None,
                "etaAfter": after.get("eta_hours") if after else None,
                "scoreAfter": risk_after.score,
                "levelAfter": risk_after.level,
            },
            "H4",
        )
        ripple_dict = {
            "trigger_shipment_id": ripple.trigger_shipment_id,
            "trigger_event_type": ripple.trigger_event_type,
            "affected_shipments": [
                asdict(a) for a in ripple.affected_shipments
            ],
            "affected_count": ripple.affected_count,
            "max_risk_increase": round(ripple.max_risk_increase, 2),
            "summary": ripple.summary,
        }
        return {"event_logged": True, "ripple": _round_floats(ripple_dict)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ripple/{shipment_id}")
def get_ripple(
    shipment_id: str, event_type: str = "roadblock"
) -> dict:
    """Get ripple impact for a shipment and event type."""
    try:
        ripple = find_affected_shipments(shipment_id, event_type)
        out = {
            "trigger_shipment_id": ripple.trigger_shipment_id,
            "trigger_event_type": ripple.trigger_event_type,
            "affected_shipments": [asdict(a) for a in ripple.affected_shipments],
            "affected_count": ripple.affected_count,
            "max_risk_increase": round(ripple.max_risk_increase, 2),
            "summary": ripple.summary,
        }
        return _round_floats(out)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/outcome")
def post_outcome(req: OutcomeRequest) -> dict:
    """Log outcome and run weight adjustment."""
    try:
        log_outcome(
            shipment_id=req.shipment_id,
            predicted_level=req.predicted_level,
            predicted_score=req.predicted_score,
            actual_outcome=req.actual_outcome,
        )
        shipment = get_shipment(req.shipment_id)
        if shipment is None:
            raise ValueError(f"Shipment {req.shipment_id} not found")
        current_eta = float(shipment.get("eta_hours") or 0.0)
        if req.actual_outcome == "delayed":
            update_shipment(
                req.shipment_id,
                status="delayed",
                eta_hours=round(current_eta + 1.5, 2),
            )
        elif req.actual_outcome == "on_time":
            update_shipment(
                req.shipment_id,
                status="on_time",
                eta_hours=round(max(0.0, current_eta - 1.0), 2),
            )
        adj = adjust_weights()
        return {"outcome_logged": True, "weight_adjustment": adj}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/analyse")
def agent_analyse(req: AgentRequest) -> dict:
    """Run agent and return recommendation."""
    if run_agent is None:
        raise HTTPException(
            status_code=500,
            detail=f"Agent not available: {_agent_error or 'Unknown error'}",
        )
    try:
        rec, ripple = run_agent(req.shipment_id, req.event_description)
        ripple_dict = {
            "trigger_shipment_id": ripple.trigger_shipment_id,
            "trigger_event_type": ripple.trigger_event_type,
            "affected_shipments": [asdict(a) for a in ripple.affected_shipments],
            "affected_count": ripple.affected_count,
            "max_risk_increase": round(ripple.max_risk_increase, 2),
            "summary": ripple.summary,
        }
        return {"recommendation": rec, "ripple": ripple_dict}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
