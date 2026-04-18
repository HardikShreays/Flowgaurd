"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { SimResult } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface DecisionPanelProps {
  shipmentId: string | null;
  onOutcomeLogged?: () => void;
  refreshKey?: number;
}

function levelFromScore(score: number): "LOW" | "MEDIUM" | "HIGH" {
  if (score < 30) return "LOW";
  if (score < 60) return "MEDIUM";
  return "HIGH";
}

export function DecisionPanel({
  shipmentId,
  onOutcomeLogged,
  refreshKey,
}: DecisionPanelProps) {
  const [sim, setSim] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcomeSuccess, setOutcomeSuccess] = useState(false);

  const fetchDecision = useCallback(async () => {
    if (!shipmentId) {
      setSim(null);
      setError(null);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDecision(shipmentId);
      setSim(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load decision");
      setSim(null);
    } finally {
      setLoading(false);
    }
  }, [shipmentId]);

  useEffect(() => {
    fetchDecision();
  }, [fetchDecision, refreshKey]);

  useEffect(() => {
    if (!shipmentId) return;
    const interval = setInterval(fetchDecision, 30000);
    return () => clearInterval(interval);
  }, [shipmentId, fetchDecision]);

  const handleOutcome = async (actual_outcome: "delayed" | "on_time") => {
    if (!shipmentId || !sim) return;
    try {
      const predicted_level = levelFromScore(sim.route_a_risk);
      await api.postOutcome({
        shipment_id: shipmentId,
        predicted_level,
        predicted_score: sim.route_a_risk,
        actual_outcome,
      });
      setOutcomeSuccess(true);
      onOutcomeLogged?.();
      setTimeout(() => setOutcomeSuccess(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to log outcome");
    }
  };

  if (!shipmentId) {
    return (
      <div className="flex items-center justify-center min-h-[200px] text-muted-foreground text-sm">
        Select a shipment to view route options.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-32 w-full rounded-lg" />
      </div>
    );
  }

  if (error || !sim) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600 text-sm">
        {error || "No decision data"}
      </div>
    );
  }

  const isARec = sim.recommendation === "A";
  const isBRec = sim.recommendation === "B";

  return (
    <div className="flex flex-col gap-4 p-4">
      {outcomeSuccess && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-green-700 text-sm">
          Outcome logged successfully.
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <Card
          className={cn(
            "rounded-lg border bg-card shadow-sm p-4",
            isARec && "ring-2 ring-green-500 border-green-300"
          )}
        >
          <CardHeader className="p-0 pb-2 flex flex-row items-center justify-between">
            <span className="font-semibold">Route A</span>
            {isARec && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                Recommended
              </span>
            )}
          </CardHeader>
          <CardContent className="p-0 space-y-1 text-sm">
            <p className="text-muted-foreground">{sim.route_a_id}</p>
            <p>Risk: {sim.route_a_risk}</p>
            <p>Distance: {sim.route_a_distance_km} km</p>
            <p>Hours: {sim.route_a_hours}h</p>
            <p>Price: ₹{sim.route_a_toll}</p>
          </CardContent>
        </Card>
        <Card
          className={cn(
            "rounded-lg border bg-card shadow-sm p-4",
            isBRec && "ring-2 ring-green-500 border-green-300"
          )}
        >
          <CardHeader className="p-0 pb-2 flex flex-row items-center justify-between">
            <span className="font-semibold">Route B</span>
            {isBRec && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                Recommended
              </span>
            )}
          </CardHeader>
          <CardContent className="p-0 space-y-1 text-sm">
            <p className="text-muted-foreground">{sim.route_b_id}</p>
            <p>Risk: {sim.route_b_risk}</p>
            <p>Distance: {sim.route_b_distance_km} km</p>
            <p>Hours: {sim.route_b_hours}h</p>
            <p>Price: ₹{sim.route_b_toll}</p>
          </CardContent>
        </Card>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div
          className={cn(
            "rounded-lg border p-4 text-center",
            sim.risk_delta <= 0
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-600"
          )}
        >
          <p className="text-xs text-muted-foreground">Risk Δ</p>
          <p className="font-semibold">{sim.risk_delta >= 0 ? "+" : ""}{sim.risk_delta}</p>
        </div>
        <div className="rounded-lg border border-muted p-4 text-center">
          <p className="text-xs text-muted-foreground">Time Δ</p>
          <p className="font-semibold">
            {sim.time_delta_hours >= 0 ? "+" : ""}{sim.time_delta_hours}h
          </p>
        </div>
        <div
          className={cn(
            "rounded-lg border p-4 text-center",
            sim.cost_delta_inr <= 0
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-600"
          )}
        >
          <p className="text-xs text-muted-foreground">Cost Δ</p>
          <p className="font-semibold">
            {sim.cost_delta_inr >= 0 ? "+" : ""}₹{sim.cost_delta_inr}
          </p>
        </div>
      </div>
      <div className="rounded-lg border border-muted bg-muted/30 p-4 text-sm text-muted-foreground">
        {sim.reason}
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={() => handleOutcome("delayed")}
          className="flex-1"
        >
          Mark as Delayed
        </Button>
        <Button
          variant="outline"
          onClick={() => handleOutcome("on_time")}
          className="flex-1"
        >
          Mark as On Time
        </Button>
      </div>
    </div>
  );
}
