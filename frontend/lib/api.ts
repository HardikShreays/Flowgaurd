import axios from "axios";
import type {
  RiskResult,
  SimResult,
  RippleResult,
  DriverEvent,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const api = {
  getAllShipments: () =>
    axios.get<RiskResult[]>(`${BASE}/shipments`).then((r) => r.data),

  getShipment: (id: string) =>
    axios.get<RiskResult>(`${BASE}/shipments/${id}`).then((r) => r.data),

  getDecision: (id: string) =>
    axios.get<SimResult>(`${BASE}/decide/${id}`).then((r) => r.data),

  postEvent: (event: DriverEvent) =>
    axios.post(`${BASE}/event`, event).then((r) => r.data),

  getRipple: (id: string, eventType = "roadblock") =>
    axios
      .get<RippleResult>(`${BASE}/ripple/${id}?event_type=${eventType}`)
      .then((r) => r.data),

  postOutcome: (data: {
    shipment_id: string;
    predicted_level: string;
    predicted_score: number;
    actual_outcome: string;
  }) => axios.post(`${BASE}/outcome`, data).then((r) => r.data),

  analyseWithAgent: (shipment_id: string, event_description: string) =>
    axios
      .post<{ recommendation: string; ripple: RippleResult }>(
        `${BASE}/agent/analyse`,
        { shipment_id, event_description }
      )
      .then((r) => r.data),
};
