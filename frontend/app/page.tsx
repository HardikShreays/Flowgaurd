"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { ShipmentList } from "@/components/ShipmentList";
import { DecisionPanel } from "@/components/DecisionPanel";
import { DriverPanel } from "@/components/DriverPanel";
import { RippleGraph } from "@/components/RippleGraph";
import { AgentOutput } from "@/components/AgentOutput";
import { RiskHistoryChart } from "@/components/RiskHistoryChart";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import type { RiskResult, RippleResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const TAB_IDS = {
  DECISION: "decision",
  DRIVER: "driver",
  RIPPLE: "ripple",
  AI: "ai",
  RISK: "risk",
} as const;

export default function DashboardPage() {
  const [selectedShipment, setSelectedShipment] = useState<RiskResult | null>(
    null
  );
  const [allShipments, setAllShipments] = useState<RiskResult[]>([]);
  const [rippleData, setRippleData] = useState<RippleResult | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState<
    (typeof TAB_IDS)[keyof typeof TAB_IDS]
  >(TAB_IDS.DECISION);
  const [currentTime, setCurrentTime] = useState("--:--:--");

  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };

    updateTime();
    const interval = setInterval(() => {
      updateTime();
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectShipment = (shipment: RiskResult) => {
    setSelectedShipment(shipment);
    setActiveTab(TAB_IDS.DECISION);
  };

  const handleEventFired = (ripple: RippleResult) => {
    setRippleData(ripple);
    setRefreshKey((k) => k + 1);
    setActiveTab(TAB_IDS.RIPPLE);
  };

  const displayedShipment = useMemo(() => {
    if (!selectedShipment) return null;
    const fresh = allShipments.find(
      (s) => s.shipment_id === selectedShipment.shipment_id
    );
    return fresh ?? selectedShipment;
  }, [selectedShipment, allShipments]);

  const handleShipmentsLoaded = useCallback((shipments: RiskResult[]) => {
    setAllShipments(shipments);
    if (shipments.length === 0) {
      setSelectedShipment(null);
      return;
    }
    setSelectedShipment((current) => {
      if (!current) return shipments[0];
      const fresh = shipments.find((s) => s.shipment_id === current.shipment_id);
      return fresh ?? shipments[0];
    });
  }, []);

  const handleAnalysisComplete = (data: {
    recommendation: string;
    ripple: RippleResult;
  }) => {
    setRippleData(data.ripple);
    setRefreshKey((k) => k + 1);
    setActiveTab(TAB_IDS.RIPPLE);
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <h1 className="font-bold text-lg">FlowGuard Control Tower</h1>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2 text-sm text-muted-foreground">
            <span
              className={cn(
                "h-2 w-2 rounded-full bg-green-500 animate-pulse"
              )}
            />
            Live
          </span>
          <span className="text-sm text-muted-foreground tabular-nums">
            {currentTime}
          </span>
        </div>
      </header>

      <div className="flex flex-1 flex-col md:flex-row min-h-0">
        <aside className="w-full md:w-[320px] md:min-w-[320px] border-r flex flex-col overflow-hidden">
          <ShipmentList
            onSelect={handleSelectShipment}
            selectedId={selectedShipment?.shipment_id ?? null}
            onShipmentsLoaded={handleShipmentsLoaded}
            refreshKey={refreshKey}
          />
        </aside>

        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {!selectedShipment ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-12 text-center text-muted-foreground">
              <p className="text-base font-medium text-foreground">
                No shipment selected
              </p>
              <p className="max-w-md text-sm">
                Choose a shipment from the list on the left to open Decision,
                Driver Event, Ripple Impact, AI Analysis, and Risk History.
              </p>
            </div>
          ) : (
            <Tabs
              value={activeTab}
              onValueChange={(v) =>
                setActiveTab(v as (typeof TAB_IDS)[keyof typeof TAB_IDS])
              }
              className="flex flex-col flex-1 min-h-0"
            >
              <div className="border-b px-4 pt-4 pb-3 space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1 min-w-0">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Active shipment
                    </p>
                    <h2 className="text-xl font-semibold tracking-tight truncate">
                      {displayedShipment?.shipment_id}
                    </h2>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {displayedShipment?.recommendation}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-xs",
                        displayedShipment?.level === "HIGH" &&
                          "border-red-200 bg-red-50 text-red-700",
                        displayedShipment?.level === "MEDIUM" &&
                          "border-amber-200 bg-amber-50 text-amber-800",
                        displayedShipment?.level === "LOW" &&
                          "border-emerald-200 bg-emerald-50 text-emerald-800"
                      )}
                    >
                      {displayedShipment?.level} risk
                    </Badge>
                    <span className="text-sm tabular-nums">
                      <span className="font-semibold text-foreground">
                        {displayedShipment?.score}
                      </span>
                      <span className="text-muted-foreground"> /100</span>
                    </span>
                    {displayedShipment?.eta_hours != null && (
                      <span className="text-xs text-muted-foreground">
                        ETA {displayedShipment.eta_hours}h
                      </span>
                    )}
                    {displayedShipment?.status === "delayed" && (
                      <Badge
                        variant="outline"
                        className="text-xs border-red-200 bg-red-50 text-red-700"
                      >
                        Delayed
                      </Badge>
                    )}
                  </div>
                </div>
                <TabsList className="w-full justify-start h-10">
                  <TabsTrigger value={TAB_IDS.DECISION}>Decision</TabsTrigger>
                  <TabsTrigger value={TAB_IDS.DRIVER}>Driver Event</TabsTrigger>
                  <TabsTrigger value={TAB_IDS.RIPPLE}>Ripple Impact</TabsTrigger>
                  <TabsTrigger value={TAB_IDS.AI}>AI Analysis</TabsTrigger>
                  <TabsTrigger value={TAB_IDS.RISK}>Risk History</TabsTrigger>
                </TabsList>
              </div>

              <div className="flex-1 overflow-auto">
                <TabsContent
                  value={TAB_IDS.DECISION}
                  className="m-0 min-h-[300px]"
                >
                  <DecisionPanel
                    shipmentId={selectedShipment.shipment_id}
                    onOutcomeLogged={() => setRefreshKey((k) => k + 1)}
                    refreshKey={refreshKey}
                  />
                </TabsContent>
                <TabsContent
                  value={TAB_IDS.DRIVER}
                  className="m-0 min-h-[300px]"
                >
                  <DriverPanel
                    shipmentId={selectedShipment.shipment_id}
                    onEventFired={handleEventFired}
                  />
                </TabsContent>
                <TabsContent
                  value={TAB_IDS.RIPPLE}
                  className="m-0 min-h-[300px]"
                >
                  <RippleGraph ripple={rippleData} allShipments={allShipments} />
                </TabsContent>
                <TabsContent value={TAB_IDS.AI} className="m-0 min-h-[300px]">
                  <AgentOutput
                    shipmentId={selectedShipment.shipment_id}
                    eventDescription="roadblock reported on primary highway"
                    onAnalysisComplete={handleAnalysisComplete}
                  />
                </TabsContent>
                <TabsContent value={TAB_IDS.RISK} className="m-0 min-h-[300px]">
                  <RiskHistoryChart
                    shipmentId={selectedShipment.shipment_id}
                  />
                </TabsContent>
              </div>
            </Tabs>
          )}
        </main>
      </div>
    </div>
  );
}
