export interface TopFactor {
  name: string;
  contribution: number;
}

export interface RiskResult {
  shipment_id: string;
  score: number;
  level: "LOW" | "MEDIUM" | "HIGH";
  top_factors: TopFactor[];
  recommendation: string;
  timestamp: string;
  status?: string;
  eta_hours?: number;
  recommended_route?: "A" | "B" | null;
  route_a_risk?: number;
  route_b_risk?: number;
  recommended_route_risk?: number | null;
}

export interface SimResult {
  shipment_id: string;
  route_a_id: string;
  route_a_risk: number;
  route_a_distance_km: number;
  route_a_hours: number;
  route_a_toll: number;
  route_b_id: string;
  route_b_risk: number;
  route_b_distance_km: number;
  route_b_hours: number;
  route_b_toll: number;
  cost_delta_inr: number;
  time_delta_hours: number;
  risk_delta: number;
  recommendation: string;
  reason: string;
}

export interface AffectedShipment {
  shipment_id: string;
  original_risk: number;
  new_risk: number;
  risk_increase: number;
  shared_element: string;
}

export interface RippleResult {
  trigger_shipment_id: string;
  trigger_event_type: string;
  affected_shipments: AffectedShipment[];
  affected_count: number;
  max_risk_increase: number;
  summary: string;
}

export interface DriverEvent {
  shipment_id: string;
  event_type: string;
  location: string;
  severity: string;
  highway: string;
}

export interface RiskHistoryPoint {
  shipment_id: string;
  score: number;
  level: string;
  timestamp: string;
}
