"use client";

import { useEffect, useRef, useState } from "react";
import type { GeoFeature, TimeRange } from "@/types";

// Leaflet is browser-only — dynamic import prevents SSR crash
let L: typeof import("leaflet") | null = null;

const HAZARD_LABELS: Record<string, string> = {
  pothole: "Pothole",
  flooding: "Flooding",
  trash: "Fly-tipping / Litter",
  broken_infrastructure: "Broken Infrastructure",
  graffiti: "Graffiti",
  housing_defect: "Housing Defect",
};

interface Props {
  features: GeoFeature[];
  timeRange: TimeRange;
  onFeatureClick?: (feature: GeoFeature) => void;
}

export default function HazardMap({ features, timeRange, onFeatureClick }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<import("leaflet").Map | null>(null);
  const markersRef = useRef<import("leaflet").LayerGroup | null>(null);
  const [ready, setReady] = useState(false);

  // Initialise Leaflet once
  useEffect(() => {
    let cancelled = false;

    import("leaflet").then((leaflet) => {
      if (cancelled || !mapRef.current || mapInstanceRef.current) return;
      L = leaflet;

      // Fix default icon path issue in Next.js
      delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      const map = L.map(mapRef.current!).setView([54.5, -2.0], 6); // UK centre

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
      markersRef.current = L.layerGroup().addTo(map);
      setReady(true);
    });

    return () => {
      cancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        markersRef.current = null;
      }
    };
  }, []);

  // Update markers when features change
  useEffect(() => {
    if (!ready || !L || !markersRef.current) return;

    markersRef.current.clearLayers();

    features.forEach((feature) => {
      const [lon, lat] = feature.geometry.coordinates;
      const { colour, hazard_type, severity_score, summary, location_name, source_url, upvotes, event_at } =
        feature.properties;

      const icon = L!.divIcon({
        className: "",
        html: `
          <div style="
            width: 14px; height: 14px;
            background: ${colour};
            border: 2px solid rgba(255,255,255,0.8);
            border-radius: 50%;
            box-shadow: 0 1px 4px rgba(0,0,0,0.6);
            opacity: ${0.5 + severity_score / 200};
          "></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L!.marker([lat, lon], { icon });

      const dateStr = event_at
        ? new Date(event_at).toLocaleDateString("en-GB", {
            day: "numeric", month: "short", year: "numeric",
          })
        : "Unknown date";

      marker.bindPopup(`
        <div style="min-width:220px; font-family: system-ui, sans-serif;">
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
            <span style="
              background:${colour}; color:#fff; padding:2px 8px;
              border-radius:9999px; font-size:11px; font-weight:600; text-transform:uppercase;
            ">${HAZARD_LABELS[hazard_type] ?? hazard_type}</span>
            <span style="font-size:12px; color:#666;">Severity: <b>${severity_score.toFixed(0)}/100</b></span>
          </div>
          ${location_name ? `<p style="font-size:12px; color:#444; margin:0 0 4px;">${location_name}</p>` : ""}
          ${summary ? `<p style="font-size:13px; margin:0 0 6px; color:#222;">${summary.slice(0, 180)}${summary.length > 180 ? "…" : ""}</p>` : ""}
          <div style="font-size:11px; color:#888; display:flex; justify-content:space-between;">
            <span>${dateStr}</span>
            <span>${upvotes} upvotes</span>
          </div>
          ${source_url ? `<a href="${source_url}" target="_blank" rel="noopener"
            style="display:block; margin-top:6px; font-size:11px; color:#3b82f6;">View original post →</a>` : ""}
        </div>
      `);

      marker.on("click", () => onFeatureClick?.(feature));
      marker.addTo(markersRef.current!);
    });
  }, [features, ready, onFeatureClick]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full rounded-lg" />
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 rounded-lg">
          <span className="text-gray-400 text-sm">Loading map...</span>
        </div>
      )}
    </div>
  );
}
