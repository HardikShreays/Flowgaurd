"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { RiskResult } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ShipmentListProps {
  onSelect: (shipment: RiskResult) => void;
  selectedId: string | null;
  onShipmentsLoaded?: (shipments: RiskResult[]) => void;
  refreshKey?: number;
}

const levelStyles = {
  HIGH: "text-red-600 bg-red-50 border-red-200",
  MEDIUM: "text-amber-600 bg-amber-50 border-amber-200",
  LOW: "text-green-600 bg-green-50 border-green-200",
} as const;

export function ShipmentList({ onSelect, selectedId, onShipmentsLoaded, refreshKey }: ShipmentListProps) {
  const [shipments, setShipments] = useState<RiskResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchShipments = useCallback(async () => {
    try {
      setError(null);
      const data = await api.getAllShipments();
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H2",location:"ShipmentList.tsx:fetchShipments:success",message:"Shipments list refreshed",data:{count:data.length,top:data.slice(0,3).map((s)=>({shipmentId:s.shipment_id,score:s.score,status:s.status,etaHours:s.eta_hours}))},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      setShipments(data);
      onShipmentsLoaded?.(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load shipments");
      setShipments([]);
    } finally {
      setLoading(false);
    }
  }, [onShipmentsLoaded]);

  useEffect(() => {
    // #region agent log
    fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H2",location:"ShipmentList.tsx:useEffect:refreshKey",message:"Shipment list effect triggered",data:{refreshKey:refreshKey ?? null},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    fetchShipments();
  }, [fetchShipments, refreshKey]);

  useEffect(() => {
    const interval = setInterval(fetchShipments, 30000);
    return () => clearInterval(interval);
  }, [fetchShipments]);

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
      </div>
    );
  }

  const highCount = shipments.filter((s) => s.level === "HIGH").length;
  const mediumCount = shipments.filter((s) => s.level === "MEDIUM").length;

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="text-xs text-muted-foreground border-b pb-2">
        {shipments.length} shipments · {highCount} high risk · {mediumCount}{" "}
        medium
      </div>
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600">
          {error}
        </div>
      )}
      <div className="flex flex-col gap-3 overflow-auto">
        {shipments.map((shipment) => (
          <Card
            key={shipment.shipment_id}
            className={cn(
              "cursor-pointer transition-all rounded-lg border bg-card shadow-sm p-4",
              selectedId === shipment.shipment_id
                ? "ring-2 ring-primary border-primary"
                : "hover:border-muted-foreground/30"
            )}
            onClick={() => onSelect(shipment)}
          >
            <CardHeader className="p-0 pb-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm">
                  {shipment.shipment_id}
                </span>
                <Badge
                  className={cn(
                    "text-xs border",
                    levelStyles[shipment.level] || levelStyles.MEDIUM
                  )}
                  variant="outline"
                >
                  {shipment.level}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-0 space-y-2">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold">{shipment.score}</span>
                <span className="text-xs text-muted-foreground">/100</span>
                {shipment.status === "delayed" && (
                  <span className="ml-1 text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
                    Delayed
                  </span>
                )}
              </div>
              {shipment.eta_hours != null && (
                <p className="text-xs text-muted-foreground">
                  ETA: {shipment.eta_hours}h
                </p>
              )}
              {shipment.recommended_route_risk != null && (
                <p className="text-xs text-muted-foreground">
                  Recommended Route {shipment.recommended_route}:{" "}
                  <span className="font-medium text-foreground">
                    {shipment.recommended_route_risk}
                  </span>
                  /100
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                {shipment.recommendation}
              </p>
              <div className="flex flex-wrap gap-1">
                {shipment.top_factors.slice(0, 3).map((f) => (
                  <span
                    key={f.name}
                    className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                  >
                    {f.name.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
