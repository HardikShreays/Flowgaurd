"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { RippleResult } from "@/lib/types";
import { Button } from "@/components/ui/button";

interface AgentOutputProps {
  shipmentId: string | null;
  eventDescription: string;
  onAnalysisComplete?: (data: {
    recommendation: string;
    ripple: RippleResult;
  }) => void;
}

export function AgentOutput({
  shipmentId,
  eventDescription,
  onAnalysisComplete,
}: AgentOutputProps) {
  const [description, setDescription] = useState(eventDescription);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [ripple, setRipple] = useState<RippleResult | null>(null);

  useEffect(() => {
    setDescription(eventDescription);
  }, [eventDescription]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyse = async () => {
    if (!shipmentId) return;
    try {
      setLoading(true);
      setError(null);
      setRecommendation(null);
      setRipple(null);
      const res = await api.analyseWithAgent(shipmentId, description);
      setRecommendation(res.recommendation);
      setRipple(res.ripple);
      onAnalysisComplete?.({ recommendation: res.recommendation, ripple: res.ripple });
    } catch (e) {
      setError("Agent unavailable. Check API connection.");
      setRecommendation(null);
      setRipple(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-col gap-2">
        <label className="text-xs font-medium text-muted-foreground">
          Event description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full min-h-[100px] rounded-lg border px-3 py-2 text-sm"
          placeholder="Describe the logistics event..."
        />
      </div>
      <Button
        onClick={handleAnalyse}
        disabled={!shipmentId || loading}
      >
        {loading ? (
          <span className="flex items-center gap-1">
            AI is reasoning
            <span className="animate-pulse">.</span>
          </span>
        ) : (
          "Analyse with AI"
        )}
      </Button>
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}
      {recommendation && (
        <div className="space-y-4">
          <div className="rounded-lg border-l-4 border-l-teal-500 border bg-muted/30 p-4 text-sm">
            {recommendation}
          </div>
          {ripple && ripple.affected_shipments.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-xs font-medium text-amber-800 mb-2">
                Affected shipments ({ripple.affected_count}):
              </p>
              <div className="flex flex-wrap gap-2">
                {ripple.affected_shipments.map((a) => (
                  <div
                    key={a.shipment_id}
                    className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs"
                  >
                    <span className="font-medium">{a.shipment_id}</span>
                    <span className="text-muted-foreground ml-1">
                      ({a.original_risk} → {a.new_risk}, +{a.risk_increase})
                    </span>
                    <span className="text-muted-foreground block text-[10px]">
                      via {a.shared_element}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {(recommendation || loading) && (
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            Powered by Gemini 1.5 Flash
          </span>
          <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            Privacy preserved
          </span>
          <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            Local data only
          </span>
        </div>
      )}
      {!shipmentId && (
        <p className="text-xs text-muted-foreground">
          Select a shipment to analyse.
        </p>
      )}
    </div>
  );
}
