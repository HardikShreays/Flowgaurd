"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import type { RiskHistoryPoint } from "@/lib/types";
import { Button } from "@/components/ui/button";

interface RiskHistoryChartProps {
  shipmentId: string | null;
}

export function RiskHistoryChart({ shipmentId }: RiskHistoryChartProps) {
  const [history, setHistory] = useState<RiskHistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlightRef = useRef(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const addPoint = useCallback(async (source: "effect" | "button" = "button") => {
    if (!shipmentId) return;
    if (inFlightRef.current) {
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H5",location:"RiskHistoryChart.tsx:addPoint:inFlightSkip",message:"Skipped duplicate addPoint while request in flight",data:{shipmentId,source},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      return;
    }
    try {
      inFlightRef.current = true;
      setLoading(true);
      setError(null);
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H1",location:"RiskHistoryChart.tsx:addPoint:beforeGetShipment",message:"Fetching latest shipment risk point",data:{shipmentId,existingPoints:history.length,source},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      const data = await api.getShipment(shipmentId);
      const point: RiskHistoryPoint = {
        shipment_id: shipmentId,
        score: data.score,
        level: data.level,
        timestamp: data.timestamp,
      };
      setHistory((prev) => {
        const next = [...prev, point].slice(-5);
        // #region agent log
        fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H2",location:"RiskHistoryChart.tsx:addPoint:setHistory",message:"Risk history point appended",data:{shipmentId,newPointScore:point.score,newPointLevel:point.level,nextLength:next.length,lastTimestamp:point.timestamp,source},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        return next;
      });
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Failed to load risk history.");
      // #region agent log
      fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H3",location:"RiskHistoryChart.tsx:addPoint:catch",message:"Risk history point fetch failed",data:{shipmentId,error:e instanceof Error ? e.message : "unknown",source},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  }, [shipmentId]);

  useEffect(() => {
    if (shipmentId) {
      setHistory([]);
      addPoint("effect");
    } else {
      setHistory([]);
    }
  }, [shipmentId, addPoint]);

  useEffect(() => {
    if (!shipmentId || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    // #region agent log
    fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H6",location:"RiskHistoryChart.tsx:container:initialRect",message:"Risk chart container measured",data:{shipmentId,width:rect.width,height:rect.height},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
  }, [shipmentId, history.length]);

  const chartData = history.map((h) => ({
    ...h,
    time: new Date(h.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));

  const lineColor =
    history.length > 0
      ? history[history.length - 1].score < 30
        ? "#22c55e"
        : history[history.length - 1].score < 60
          ? "#f59e0b"
          : "#ef4444"
      : "#94a3b8";

  if (!shipmentId) {
    return (
      <div className="flex items-center justify-center min-h-[200px] text-muted-foreground text-sm">
        Select a shipment to view risk history.
      </div>
    );
  }

  if (history.length === 1) {
    // #region agent log
    fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H4",location:"RiskHistoryChart.tsx:render:singlePointState",message:"Risk history chart rendered in single-point state",data:{shipmentId,historyLength:history.length,hasError:!!error},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    return (
      <div className="flex flex-col gap-4 p-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-700 text-sm">
            {error}
          </div>
        )}
        <p className="text-sm text-muted-foreground">
          Risk history builds as events are fired. Click Refresh to add a data
          point.
        </p>
        <Button
          variant="outline"
          onClick={() => addPoint("button")}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh risk"}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* #region agent log */}
      {fetch("http://127.0.0.1:7808/ingest/e5913699-4ab3-4493-a02b-dddde1d5e803",{method:"POST",headers:{"Content-Type":"application/json","X-Debug-Session-Id":"8af04b"},body:JSON.stringify({sessionId:"8af04b",runId:"pre-fix",hypothesisId:"H4",location:"RiskHistoryChart.tsx:render:chartState",message:"Risk history chart rendered in chart state",data:{shipmentId,historyLength:history.length,chartDataLength:chartData.length,hasError:!!error},timestamp:Date.now()})}).catch(()=>{}), null}
      {/* #endregion */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-700 text-sm">
          {error}
        </div>
      )}
      <div ref={containerRef} className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11 }}
              stroke="#94a3b8"
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              stroke="#94a3b8"
            />
            <ReferenceLine
              y={30}
              stroke="#22c55e"
              strokeDasharray="3 3"
              label={{ value: "Low", position: "right", fontSize: 10 }}
            />
            <ReferenceLine
              y={60}
              stroke="#f59e0b"
              strokeDasharray="3 3"
              label={{ value: "Medium", position: "right", fontSize: 10 }}
            />
            <ReferenceLine
              y={100}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{ value: "High", position: "right", fontSize: 10 }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload?.[0]) {
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg border bg-white p-2 shadow-lg text-xs">
                      <p>Score: {d.score}</p>
                      <p>Level: {d.level}</p>
                      <p>Time: {d.timestamp}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke={lineColor}
              strokeWidth={2}
              dot={{ r: 4, fill: lineColor }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Button
        variant="outline"
        onClick={() => addPoint("button")}
        disabled={loading}
        size="sm"
      >
        {loading ? "Refreshing..." : "Refresh risk"}
      </Button>
    </div>
  );
}
