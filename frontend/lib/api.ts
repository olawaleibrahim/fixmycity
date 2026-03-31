import type { GeoCollection, HazardEvent, MapStats, TimeRange } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  mapEvents: (timeRange: TimeRange = "7d", hazardType?: string) =>
    get<GeoCollection>("/map/events", {
      time_range: timeRange,
      ...(hazardType ? { hazard_type: hazardType } : {}),
    }),

  mapStats: () => get<MapStats>("/map/stats"),

  events: (params?: {
    timeRange?: TimeRange;
    hazardType?: string;
    hasLocation?: boolean;
    minSeverity?: number;
    limit?: number;
  }) =>
    get<HazardEvent[]>("/events/", {
      time_range: params?.timeRange ?? "7d",
      ...(params?.hazardType ? { hazard_type: params.hazardType } : {}),
      ...(params?.hasLocation ? { has_location: "true" } : {}),
      ...(params?.minSeverity ? { min_severity: String(params.minSeverity) } : {}),
      limit: String(params?.limit ?? 100),
    }),
};
