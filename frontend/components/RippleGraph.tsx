"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { RippleResult, RiskResult } from "@/lib/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

interface RippleGraphProps {
  ripple: RippleResult | null;
  allShipments: RiskResult[];
}

const affectedShipmentIds = (r: RippleResult) =>
  new Set(r.affected_shipments.map((a) => a.shipment_id));

export function RippleGraph({ ripple, allShipments }: RippleGraphProps) {
  const { nodes, edges } = useMemo(() => {
    if (!ripple) return { nodes: [], edges: [] };

    const n: Node[] = [];
    const e: Edge[] = [];

    const triggerId = ripple.trigger_shipment_id;
    const scoreByShipment = new Map(
      allShipments.map((s) => [s.shipment_id, s.score] as const)
    );
    const affectedSet = affectedShipmentIds(ripple);
    const affectedList = ripple.affected_shipments;
    const unaffected = allShipments.filter(
      (s) => s.shipment_id !== triggerId && !affectedSet.has(s.shipment_id)
    );

    n.push({
      id: triggerId,
      type: "default",
      position: { x: 300, y: 200 },
      data: { label: `${triggerId} ${scoreByShipment.get(triggerId) ?? "-"}` },
      style: { width: 150, height: 60, background: "#dc2626", color: "white" },
    });

    const radius = 180;
    affectedList.forEach((a, i) => {
      const angle = (i / Math.max(affectedList.length, 1)) * Math.PI - Math.PI / 2;
      const x = 300 + radius * Math.cos(angle);
      const y = 200 + radius * Math.sin(angle);
      const bg =
        a.risk_increase >= 20
          ? "#ef4444"
          : a.risk_increase >= 10
            ? "#fbbf24"
            : "#d1d5db";
      n.push({
        id: a.shipment_id,
        type: "default",
        position: { x, y },
        data: {
          label: `${a.shipment_id} ${a.new_risk} (+${a.risk_increase})`,
        },
        style: { width: 120, height: 50, background: bg },
      });
      e.push({
        id: `e-${triggerId}-${a.shipment_id}`,
        source: triggerId,
        target: a.shipment_id,
        label: a.shared_element,
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed },
      });
    });

    unaffected.forEach((s, i) => {
      const x = 80 + (i % 5) * 120;
      const y = 420 + Math.floor(i / 5) * 50;
      n.push({
        id: s.shipment_id,
        type: "default",
        position: { x, y },
        data: { label: `${s.shipment_id} ${s.score}` },
        style: { width: 90, height: 36, background: "#e5e7eb" },
      });
    });

    return { nodes: n, edges: e };
  }, [ripple, allShipments]);

  if (!ripple) {
    return (
      <div className="flex items-center justify-center min-h-[300px] text-muted-foreground text-sm">
        Fire a driver event to see cascade impact.
      </div>
    );
  }

  const topImpact = [...ripple.affected_shipments].sort(
    (a, b) => b.risk_increase - a.risk_increase
  )[0];
  const uniqueLinks = new Set(
    ripple.affected_shipments.map((a) => a.shared_element)
  ).size;

  const alertVariant =
    ripple.affected_count > 2
      ? "destructive"
      : ripple.affected_count > 0
        ? "default"
        : "default";

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-lg border bg-card p-3 text-sm">
          <p className="text-xs text-muted-foreground">Trigger</p>
          <p className="font-semibold">{ripple.trigger_shipment_id}</p>
          <p className="text-xs text-muted-foreground">
            Event: {ripple.trigger_event_type}
          </p>
        </div>
        <div className="rounded-lg border bg-card p-3 text-sm">
          <p className="text-xs text-muted-foreground">Most impacted</p>
          <p className="font-semibold">
            {topImpact ? topImpact.shipment_id : "None"}
          </p>
          <p className="text-xs text-muted-foreground">
            {topImpact ? `+${topImpact.risk_increase} risk via ${topImpact.shared_element}` : "No downstream risk increase"}
          </p>
        </div>
        <div className="rounded-lg border bg-card p-3 text-sm">
          <p className="text-xs text-muted-foreground">Network spread</p>
          <p className="font-semibold">{ripple.affected_count} shipments</p>
          <p className="text-xs text-muted-foreground">
            Across {uniqueLinks} shared links
          </p>
        </div>
      </div>
      <div
        className="h-[400px] rounded-lg border bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:20px_20px]"
        style={{ backgroundSize: "20px 20px" }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.2}
          maxZoom={1.5}
        >
          <Background gap={20} size={1} color="#cbd5e1" />
          <Controls />
        </ReactFlow>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="inline-flex items-center gap-1 rounded border bg-red-50 px-2 py-1 text-red-700">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          high impact (≥20)
        </span>
        <span className="inline-flex items-center gap-1 rounded border bg-amber-50 px-2 py-1 text-amber-700">
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          medium impact (10-19)
        </span>
        <span className="inline-flex items-center gap-1 rounded border bg-slate-50 px-2 py-1 text-slate-700">
          <span className="h-2 w-2 rounded-full bg-slate-300" />
          low impact (0-9)
        </span>
      </div>
      <Alert
        className={cn(
          ripple.affected_count > 2 && "border-red-200 bg-red-50",
          ripple.affected_count > 0 &&
            ripple.affected_count <= 2 &&
            "border-amber-200 bg-amber-50",
          ripple.affected_count === 0 && "border-green-200 bg-green-50"
        )}
        variant={alertVariant}
      >
        <AlertDescription>
          <span className="font-medium">{ripple.affected_count} affected.</span>{" "}
          {ripple.summary}
        </AlertDescription>
      </Alert>
    </div>
  );
}
