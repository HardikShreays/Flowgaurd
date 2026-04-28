"""FlowGuard database module. SQLite as single source of truth."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH: Path = Path(
    os.getenv(
        "DB_PATH",
        str(Path(__file__).resolve().parent.parent / "flowguard.db"),
    )
)


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables and indexes if they do not exist."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS shipments (
                shipment_id TEXT PRIMARY KEY,
                origin TEXT,
                destination TEXT,
                route_id TEXT,
                status TEXT,
                cargo_type TEXT,
                weight_kg REAL,
                departure_time TEXT,
                eta_hours REAL,
                current_location TEXT,
                priority TEXT
            );

            CREATE TABLE IF NOT EXISTS routes (
                route_id TEXT PRIMARY KEY,
                name TEXT,
                origin TEXT,
                destination TEXT,
                primary_highway TEXT,
                distance_km REAL,
                estimated_hours REAL,
                checkpoints TEXT,
                toll_cost_inr REAL,
                alternative_route_id TEXT
            );

            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                city TEXT,
                state TEXT,
                connected_routes TEXT,
                avg_processing_time_hours REAL,
                congestion_level TEXT
            );

            CREATE TABLE IF NOT EXISTS delay_factors (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS driver_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id TEXT,
                event_type TEXT,
                location TEXT,
                severity TEXT,
                highway TEXT,
                timestamp TEXT,
                resolved INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS risk_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id TEXT,
                score REAL,
                level TEXT,
                top_factors TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id TEXT,
                predicted_level TEXT,
                predicted_score REAL,
                actual_outcome TEXT,
                was_correct INTEGER,
                timestamp TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_driver_events_shipment ON driver_events(shipment_id);
            CREATE INDEX IF NOT EXISTS idx_risk_history_shipment ON risk_history(shipment_id);
            CREATE INDEX IF NOT EXISTS idx_outcomes_shipment ON outcomes(shipment_id);
        """)
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a sqlite3.Row to a dict. Returns None if row is None."""
    if row is None:
        return None
    return dict(row)


def get_all_shipments() -> list[dict[str, Any]]:
    """Return all shipments as a list of dicts."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM shipments")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_shipment(shipment_id: str) -> dict[str, Any] | None:
    """Return one shipment by id, or None if not found."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM shipments WHERE shipment_id = ?",
            (shipment_id,)
        )
        row = cur.fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def update_shipment(
    shipment_id: str,
    *,
    status: str | None = None,
    eta_hours: float | None = None,
    current_location: str | None = None,
) -> None:
    """Update shipment fields. Only provided fields are updated."""
    conn = get_connection()
    try:
        updates = []
        params: list[Any] = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if eta_hours is not None:
            updates.append("eta_hours = ?")
            params.append(eta_hours)
        if current_location is not None:
            updates.append("current_location = ?")
            params.append(current_location)
        if not updates:
            return
        params.append(shipment_id)
        conn.execute(
            f"UPDATE shipments SET {', '.join(updates)} WHERE shipment_id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()


def get_route(route_id: str) -> dict[str, Any] | None:
    """Return one route by id, or None if not found. Parses checkpoints from JSON."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM routes WHERE route_id = ?",
            (route_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("checkpoints"):
            d["checkpoints"] = json.loads(d["checkpoints"])
        return d
    finally:
        conn.close()


def get_node_by_city(city: str) -> dict[str, Any] | None:
    """Return one node matching city name, or None if not found. Parses connected_routes from JSON."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM nodes WHERE city = ?",
            (city,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("connected_routes"):
            d["connected_routes"] = json.loads(d["connected_routes"])
        else:
            d["connected_routes"] = []
        return d
    finally:
        conn.close()


def get_delay_factors() -> dict[str, Any]:
    """Reconstruct the full delay_factors dict from the database."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT key, value FROM delay_factors")
        result: dict[str, Any] = {}
        for row in cur.fetchall():
            result[row["key"]] = json.loads(row["value"])
        return result
    finally:
        conn.close()


def update_delay_factor(key: str, value: Any) -> None:
    """Update or insert a delay_factors key-value pair."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO delay_factors (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        conn.commit()
    finally:
        conn.close()


def log_risk_score(
    shipment_id: str,
    score: float,
    level: str,
    top_factors: list[Any],
) -> None:
    """Insert a row into risk_history."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO risk_history (shipment_id, score, level, top_factors, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (
                shipment_id,
                score,
                level,
                json.dumps(top_factors),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def log_driver_event(
    shipment_id: str,
    event_type: str,
    location: str,
    severity: str,
    highway: str,
) -> None:
    """Insert a row into driver_events."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO driver_events (shipment_id, event_type, location, severity, highway, timestamp, resolved)
               VALUES (?, ?, ?, ?, ?, ?, 0)""",
            (
                shipment_id,
                event_type,
                location,
                severity,
                highway,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def log_outcome(
    shipment_id: str,
    predicted_level: str,
    predicted_score: float,
    actual_outcome: str,
) -> None:
    """Insert a row into outcomes. Computes was_correct from prediction vs actual."""
    pred_upper = predicted_level.upper()
    if pred_upper == "HIGH" and actual_outcome == "delayed":
        was_correct = 1
    elif pred_upper in ("LOW", "MEDIUM") and actual_outcome == "on_time":
        was_correct = 1
    else:
        was_correct = 0

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO outcomes (shipment_id, predicted_level, predicted_score, actual_outcome, was_correct, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                shipment_id,
                predicted_level,
                predicted_score,
                actual_outcome,
                was_correct,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_outcomes(limit: int = 20) -> list[dict[str, Any]]:
    """Return most recent outcomes, ordered by timestamp descending."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM outcomes ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_risk_history(shipment_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent risk_history rows for a shipment. Parses top_factors from JSON."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT * FROM risk_history WHERE shipment_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (shipment_id, limit),
        )
        rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get("top_factors"):
                d["top_factors"] = json.loads(d["top_factors"])
            result.append(d)
        return result
    finally:
        conn.close()
