"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { RippleResult } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DriverPanelProps {
  shipmentId: string | null;
  onEventFired: (ripple: RippleResult) => void;
}

const EVENTS = [
  { type: "roadblock" as const, label: "Roadblock", severity: "high" as const },
  { type: "traffic_jam" as const, label: "Traffic Jam", severity: "medium" as const },
  { type: "checkpoint_delay" as const, label: "Checkpoint Delay", severity: "low" as const },
  { type: "weather" as const, label: "Weather Impact", severity: "low" as const },
];

export function DriverPanel({ shipmentId, onEventFired }: DriverPanelProps) {
  const [location, setLocation] = useState("NH-8 km 340");
  const [highway, setHighway] = useState("NH-8");
  const [loading, setLoading] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEvent = async (
    eventType: string,
    severity: string
  ) => {
    if (!shipmentId) return;
    try {
      setLoading(eventType);
      setSuccess(false);
      setError(null);
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H1",location:"DriverPanel.tsx:handleEvent:beforePostEvent",message:"Submitting driver event",data:{shipmentId,eventType,severity,highway,location},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      await api.postEvent({
        shipment_id: shipmentId,
        event_type: eventType,
        location,
        severity,
        highway,
      });
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H1",location:"DriverPanel.tsx:handleEvent:postEventSuccess",message:"Driver event posted successfully",data:{shipmentId,eventType},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      const ripple = await api.getRipple(shipmentId, eventType);
      onEventFired(ripple);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 4000);
    } catch (e) {
      console.error(e);
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H3",location:"DriverPanel.tsx:handleEvent:catch",message:"Driver event failed in frontend",data:{shipmentId,eventType,error:e instanceof Error ? e.message : "unknown"},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      setError(e instanceof Error ? e.message : "Failed to report event.");
    } finally {
      setLoading(null);
    }
  };

  const disabled = !shipmentId;

  return (
    <div className="flex flex-col gap-4 p-4">
      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-green-700 text-sm">
          Event reported. Ripple analysis complete.
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-700 text-sm">
          {error}
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        {EVENTS.map((ev) => (
          <Button
            key={ev.type}
            size="lg"
            variant="outline"
            disabled={disabled}
            onClick={() => handleEvent(ev.type, ev.severity)}
            className={cn(
              "h-20 flex flex-col items-center justify-center gap-1",
              disabled && "opacity-50 cursor-not-allowed"
            )}
            title={disabled ? "Select a shipment first." : undefined}
          >
            {loading === ev.type ? (
              <span className="animate-pulse">Loading...</span>
            ) : (
              <>
                <span className="text-base font-medium">{ev.label}</span>
                <span className="text-xs text-muted-foreground capitalize">
                  {ev.severity}
                </span>
              </>
            )}
          </Button>
        ))}
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium text-muted-foreground">
          Location
        </label>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="w-full rounded-lg border px-3 py-2 text-sm"
          placeholder="NH-8 km 340"
        />
        <label className="text-xs font-medium text-muted-foreground">
          Highway
        </label>
        <input
          type="text"
          value={highway}
          onChange={(e) => setHighway(e.target.value)}
          className="w-full rounded-lg border px-3 py-2 text-sm"
          placeholder="NH-8"
        />
      </div>
      {disabled && (
        <p className="text-xs text-muted-foreground">
          Select a shipment first to report an event.
        </p>
      )}
    </div>
  );
}
