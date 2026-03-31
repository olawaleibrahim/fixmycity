"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import type { GeoFeature, GeoCollection, MapStats, TimeRange } from "@/types";
import { api } from "@/lib/api";

// Leaflet must not be SSR'd
const HazardMap = dynamic(() => import("@/components/HazardMap"), { ssr: false });

export default function HomePage() {
  const [geoData, setGeoData] = useState<GeoCollection | null>(null);
  const [stats, setStats] = useState<MapStats | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>("all");
  const [activeType, setActiveType] = useState<string | null>(null);
  const [selectedFeature, setSelectedFeature] = useState<GeoFeature | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [geo, s] = await Promise.all([
        api.mapEvents(timeRange, activeType ?? undefined),
        api.mapStats(),
      ]);
      setGeoData(geo);
      setStats(s);
    } catch (err) {
      setError("Could not connect to the API. Is the backend running?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [timeRange, activeType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        stats={stats}
        selectedFeature={selectedFeature}
        timeRange={timeRange}
        onTimeRangeChange={(t) => {
          setTimeRange(t);
          setSelectedFeature(null);
        }}
        activeType={activeType}
        onTypeChange={(t) => {
          setActiveType(t);
          setSelectedFeature(null);
        }}
        totalShown={geoData?.features.length ?? 0}
      />

      <main className="flex-1 relative h-full">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-950/70">
            <div className="text-gray-300 text-sm animate-pulse">Loading events...</div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-950">
            <div className="text-center space-y-2">
              <p className="text-red-400">{error}</p>
              <button
                onClick={fetchData}
                className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-500"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {!error && (
          <HazardMap
            features={geoData?.features ?? []}
            timeRange={timeRange}
            onFeatureClick={setSelectedFeature}
          />
        )}
      </main>
    </div>
  );
}
