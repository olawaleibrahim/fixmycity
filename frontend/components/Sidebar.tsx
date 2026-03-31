"use client";

import Link from "next/link";
import type { GeoFeature, MapStats, TimeRange } from "@/types";

const HAZARD_COLOURS: Record<string, string> = {
  pothole: "#f97316",
  flooding: "#3b82f6",
  trash: "#84cc16",
  broken_infrastructure: "#a855f7",
  graffiti: "#ec4899",
  housing_defect: "#ef4444",
};

const HAZARD_LABELS: Record<string, string> = {
  pothole: "Pothole",
  flooding: "Flooding",
  trash: "Fly-tipping / Litter",
  broken_infrastructure: "Broken Infrastructure",
  graffiti: "Graffiti",
  housing_defect: "Housing Defect",
};

interface Props {
  stats: MapStats | null;
  selectedFeature: GeoFeature | null;
  timeRange: TimeRange;
  onTimeRangeChange: (t: TimeRange) => void;
  activeType: string | null;
  onTypeChange: (t: string | null) => void;
  totalShown: number;
}

export default function Sidebar({
  stats,
  selectedFeature,
  timeRange,
  onTimeRangeChange,
  activeType,
  onTypeChange,
  totalShown,
}: Props) {
  const TIME_OPTIONS: { label: string; value: TimeRange }[] = [
    { label: "Last 24h", value: "24h" },
    { label: "Last 7 days", value: "7d" },
    { label: "Last 30 days", value: "30d" },
    { label: "All time", value: "all" },
  ];

  return (
    <aside className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="p-5 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white">FixMyCity</h1>
        <p className="text-xs text-gray-400 mt-1">Urban hazard detection platform</p>
      </div>

      {/* Time filter */}
      <div className="p-4 border-b border-gray-800">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Time range
        </p>
        <div className="flex flex-wrap gap-2">
          {TIME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onTimeRangeChange(opt.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                timeRange === opt.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Type filter */}
      <div className="p-4 border-b border-gray-800">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Hazard type
        </p>
        <div className="flex flex-col gap-1">
          <button
            onClick={() => onTypeChange(null)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeType === null ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-800"
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-gray-500 flex-shrink-0" />
            All types
            {stats && (
              <span className="ml-auto text-gray-500">{stats.total}</span>
            )}
          </button>
          {Object.entries(HAZARD_LABELS).map(([type, label]) => (
            <button
              key={type}
              onClick={() => onTypeChange(activeType === type ? null : type)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeType === type ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ background: HAZARD_COLOURS[type] }}
              />
              {label}
              {stats?.by_type[type] !== undefined && (
                <span className="ml-auto text-gray-500">{stats.by_type[type]}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="p-4 border-b border-gray-800">
        <p className="text-xs text-gray-500">
          Showing <span className="text-white font-semibold">{totalShown}</span> geo-located events
        </p>
      </div>

      {/* Rankings link */}
      <div className="p-4 border-b border-gray-800">
        <Link
          href="/rankings"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gradient-to-r from-orange-900/40 to-red-900/40 border border-orange-700/30 hover:border-orange-600/50 transition-colors group"
        >
          <span className="text-xl">🔥</span>
          <div className="flex-1 min-w-0">
            <p className="text-white text-xs font-semibold group-hover:text-orange-300 transition-colors">
              Neighbourhood Rankings
            </p>
            <p className="text-gray-500 text-xs">Daily shame leaderboard</p>
          </div>
          <span className="text-gray-600 group-hover:text-gray-400 transition-colors text-xs">→</span>
        </Link>
      </div>

      {/* Selected feature detail */}
      {selectedFeature && (
        <div className="p-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Selected event
          </p>
          <div className="bg-gray-800 rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span
                className="px-2 py-0.5 rounded-full text-xs font-semibold text-white"
                style={{ background: selectedFeature.properties.colour }}
              >
                {HAZARD_LABELS[selectedFeature.properties.hazard_type] ??
                  selectedFeature.properties.hazard_type}
              </span>
              <span className="text-xs text-gray-400">
                {selectedFeature.properties.severity_score.toFixed(0)}/100
              </span>
            </div>
            {selectedFeature.properties.location_name && (
              <p className="text-xs text-gray-300 truncate">
                {selectedFeature.properties.location_name}
              </p>
            )}
            {selectedFeature.properties.summary && (
              <p className="text-xs text-gray-400 line-clamp-4">
                {selectedFeature.properties.summary}
              </p>
            )}
            {selectedFeature.properties.source_url && (
              <a
                href={selectedFeature.properties.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                View source →
              </a>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
