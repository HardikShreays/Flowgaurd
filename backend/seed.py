"""Logicore database seed script. Loads JSON files into SQLite."""

import json
from pathlib import Path

from database import get_connection, init_db

DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"


def seed() -> None:
    """Load all JSON files and populate the database. Idempotent."""
    init_db()
    conn = get_connection()

    try:
        # Load JSON files
        shipments_path = DATA_DIR / "shipments.json"
        routes_path = DATA_DIR / "routes.json"
        nodes_path = DATA_DIR / "nodes.json"
        delay_factors_path = DATA_DIR / "delay_factors.json"

        with open(shipments_path) as f:
            shipments = json.load(f)
        with open(routes_path) as f:
            routes = json.load(f)
        with open(nodes_path) as f:
            nodes = json.load(f)
        with open(delay_factors_path) as f:
            delay_factors = json.load(f)

        # Insert shipments
        for s in shipments:
            conn.execute(
                """INSERT OR IGNORE INTO shipments (
                    shipment_id, origin, destination, route_id, status,
                    cargo_type, weight_kg, departure_time, eta_hours,
                    current_location, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s["shipment_id"],
                    s["origin"],
                    s["destination"],
                    s["route_id"],
                    s["status"],
                    s["cargo_type"],
                    s["weight_kg"],
                    s["departure_time"],
                    s["eta_hours"],
                    s["current_location"],
                    s["priority"],
                ),
            )

        # Insert routes
        for r in routes:
            conn.execute(
                """INSERT OR IGNORE INTO routes (
                    route_id, name, origin, destination, primary_highway,
                    distance_km, estimated_hours, checkpoints, toll_cost_inr,
                    alternative_route_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["route_id"],
                    r["name"],
                    r["origin"],
                    r["destination"],
                    r["primary_highway"],
                    r["distance_km"],
                    r["estimated_hours"],
                    json.dumps(r["checkpoints"]),
                    r["toll_cost_inr"],
                    r["alternative_route_id"],
                ),
            )

        # Insert nodes
        for n in nodes:
            conn.execute(
                """INSERT OR IGNORE INTO nodes (
                    node_id, name, type, city, state, connected_routes,
                    avg_processing_time_hours, congestion_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    n["node_id"],
                    n["name"],
                    n["type"],
                    n["city"],
                    n["state"],
                    json.dumps(n["connected_routes"]),
                    n["avg_processing_time_hours"],
                    n["congestion_level"],
                ),
            )

        # Insert delay_factors (INSERT OR REPLACE)
        for key, value in delay_factors.items():
            conn.execute(
                "INSERT OR REPLACE INTO delay_factors (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )

        conn.commit()
        print(
            f"Seeded: {len(shipments)} shipments, {len(routes)} routes, "
            f"{len(nodes)} nodes, {len(delay_factors)} delay factor keys"
        )
        print("Database: logicore.db")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
