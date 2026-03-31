export type HazardType =
  | "pothole"
  | "flooding"
  | "trash"
  | "broken_infrastructure"
  | "graffiti"
  | "housing_defect";

export type TimeRange = "24h" | "7d" | "30d" | "all";

export interface HazardEvent {
  id: number;
  hazard_type: HazardType;
  confidence: number;
  lat: number | null;
  lon: number | null;
  location_name: string | null;
  severity_score: number;
  summary: string | null;
  source: string | null;
  source_url: string | null;
  upvotes: number;
  event_at: string | null;
}

export interface GeoFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lon, lat]
  };
  properties: {
    id: number;
    hazard_type: HazardType;
    severity_score: number;
    confidence: number;
    location_name: string | null;
    summary: string | null;
    source: string | null;
    source_url: string | null;
    upvotes: number;
    event_at: string | null;
    colour: string;
  };
}

export interface GeoCollection {
  type: "FeatureCollection";
  features: GeoFeature[];
  meta: { total: number; time_range: TimeRange };
}

export interface MapStats {
  by_type: Record<string, number>;
  total: number;
}
