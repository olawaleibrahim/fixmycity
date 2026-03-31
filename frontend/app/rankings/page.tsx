"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import type { AreaRanking, RankingsResponse, TimeRange } from "@/types";
import { api } from "@/lib/api";

// ── helpers ────────────────────────────────────────────────────────────────

const HAZARD_COLOURS: Record<string, string> = {
  pothole: "#f97316",
  flooding: "#3b82f6",
  trash: "#84cc16",
  broken_infrastructure: "#a855f7",
  graffiti: "#ec4899",
  housing_defect: "#ef4444",
};

const SCORE_GRADIENT = (score: number) => {
  if (score >= 80) return "from-red-900/60 to-red-800/40 border-red-700/50";
  if (score >= 65) return "from-orange-900/60 to-orange-800/40 border-orange-700/50";
  if (score >= 50) return "from-yellow-900/50 to-yellow-800/30 border-yellow-700/40";
  return "from-gray-800/60 to-gray-800/40 border-gray-700/50";
};

const TREND_COLOUR = (dir: string) => {
  if (dir === "up")   return "text-red-400";
  if (dir === "down") return "text-green-400";
  return "text-gray-500";
};

// ── podium ─────────────────────────────────────────────────────────────────

function PodiumCard({ area, position }: { area: AreaRanking; position: 1 | 2 | 3 }) {
  const medals = { 1: "🥇", 2: "🥈", 3: "🥉" };
  const heights = { 1: "h-44", 2: "h-36", 3: "h-32" };
  const rings = {
    1: "ring-2 ring-yellow-400/60 shadow-yellow-500/20",
    2: "ring-2 ring-gray-400/40 shadow-gray-400/10",
    3: "ring-2 ring-orange-700/40 shadow-orange-700/10",
  };
  const colour = HAZARD_COLOURS[area.primary_hazard] ?? "#6b7280";

  return (
    <div
      className={`relative flex flex-col items-center justify-end ${heights[position]}
        bg-gradient-to-b ${SCORE_GRADIENT(area.shame_score)}
        rounded-2xl border p-4 ${rings[position]} shadow-xl transition-transform hover:-translate-y-1 cursor-default`}
    >
      {/* medal */}
      <span className="absolute -top-5 text-3xl">{medals[position]}</span>

      {/* rank number faint background */}
      <span className="absolute top-2 right-3 text-6xl font-black opacity-5 select-none">
        {position}
      </span>

      {/* hazard dot */}
      <div
        className="w-3 h-3 rounded-full mb-2 ring-2 ring-white/20"
        style={{ background: colour }}
      />

      {/* area name */}
      <p className="text-white font-bold text-base text-center leading-tight mb-1">
        {area.area}
      </p>

      {/* score */}
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-2xl font-black text-white">{area.shame_score}</span>
        <span className="text-xs text-gray-400">/100</span>
      </div>

      {/* descriptor */}
      <span className="text-xs text-center text-gray-300 leading-tight mb-1">
        {area.descriptor}
      </span>

      {/* primary hazard */}
      <span className="text-xs text-gray-500">
        {area.primary_hazard_emoji} {area.event_count} events
      </span>

      {/* trend */}
      {area.trend_pct !== null && (
        <span className={`text-xs font-semibold mt-1 ${TREND_COLOUR(area.trend_direction)}`}>
          {area.trend_label}
        </span>
      )}
    </div>
  );
}

// ── score bar ──────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const colour =
    score >= 80 ? "#ef4444" :
    score >= 65 ? "#f97316" :
    score >= 50 ? "#eab308" :
    "#6b7280";

  return (
    <div className="flex items-center gap-2 w-32">
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, background: colour }}
        />
      </div>
      <span className="text-xs font-bold text-white w-8 text-right">{score}</span>
    </div>
  );
}

// ── hazard breakdown pill ──────────────────────────────────────────────────

function HazardPills({ breakdown }: { breakdown: Record<string, number> }) {
  const entries = Object.entries(breakdown)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  const EMOJI: Record<string, string> = {
    pothole: "🕳️",
    flooding: "🌊",
    trash: "🗑️",
    broken_infrastructure: "🚧",
    graffiti: "🎨",
    housing_defect: "🏚️",
  };

  return (
    <div className="flex gap-1 flex-wrap">
      {entries.map(([type, count]) => (
        <span
          key={type}
          className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400"
          style={{ borderLeft: `2px solid ${HAZARD_COLOURS[type] ?? "#6b7280"}` }}
        >
          {EMOJI[type]} {count}
        </span>
      ))}
    </div>
  );
}

// ── main leaderboard row ───────────────────────────────────────────────────

function RankRow({ area, highlight }: { area: AreaRanking; highlight?: boolean }) {
  const isTop3 = area.rank <= 3;

  return (
    <div
      className={`grid items-center gap-4 px-5 py-3.5 rounded-xl transition-colors
        ${highlight
          ? `bg-gradient-to-r ${SCORE_GRADIENT(area.shame_score)} border`
          : "hover:bg-gray-800/50 border border-transparent"
        }`}
      style={{ gridTemplateColumns: "2.5rem 1fr 9rem 10rem 5rem 7rem" }}
    >
      {/* rank */}
      <div className="flex items-center justify-center">
        <span
          className={`text-sm font-black ${
            area.rank === 1 ? "text-yellow-400 text-base" :
            area.rank === 2 ? "text-gray-300" :
            area.rank === 3 ? "text-orange-400" :
            "text-gray-600"
          }`}
        >
          {area.rank <= 3 ? ["🥇","🥈","🥉"][area.rank - 1] : `#${area.rank}`}
        </span>
      </div>

      {/* area + descriptor */}
      <div className="min-w-0">
        <p className="text-white font-semibold text-sm truncate">{area.area}</p>
        <p className="text-gray-500 text-xs truncate">{area.descriptor}</p>
      </div>

      {/* score bar */}
      <ScoreBar score={area.shame_score} />

      {/* hazard breakdown */}
      <HazardPills breakdown={area.hazard_breakdown} />

      {/* event count */}
      <p className="text-gray-400 text-xs text-right">
        <span className="text-white font-semibold">{area.event_count}</span>
        <br />events
      </p>

      {/* trend */}
      <div className={`text-xs font-medium text-right ${TREND_COLOUR(area.trend_direction)}`}>
        {area.trend_label}
        {area.trend_pct !== null && (
          <span className="block text-gray-600 font-normal">
            {area.trend_pct > 0 ? "+" : ""}{area.trend_pct}%
          </span>
        )}
      </div>
    </div>
  );
}

// ── most improved section ──────────────────────────────────────────────────

function MostImproved({ areas }: { areas: AreaRanking[] }) {
  if (!areas.length) return null;

  return (
    <div className="mt-10">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">📉</span>
        <div>
          <h2 className="text-white font-bold text-base">Most Improved</h2>
          <p className="text-gray-500 text-xs">Areas with the biggest score drop this period</p>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {areas.map((area) => (
          <div
            key={area.area}
            className="bg-green-950/30 border border-green-800/30 rounded-xl p-4"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-white font-semibold text-sm">{area.area}</p>
              <span className="text-green-400 text-xs font-bold">
                {area.trend_pct}%
              </span>
            </div>
            <p className="text-gray-500 text-xs mb-2">{area.descriptor}</p>
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <span>{area.primary_hazard_emoji}</span>
              <span>{area.event_count} events</span>
              <span>·</span>
              <span>Score: {area.shame_score}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

const TIME_OPTIONS: { label: string; value: TimeRange }[] = [
  { label: "Today",     value: "24h" },
  { label: "This Week", value: "7d" },
  { label: "This Month",value: "30d" },
  { label: "All Time",  value: "all" },
];

export default function RankingsPage() {
  const [data, setData] = useState<RankingsResponse | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRankings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.rankings(timeRange, 20));
    } catch {
      setError("Could not load rankings. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => { fetchRankings(); }, [fetchRankings]);

  const top3   = data?.rankings.slice(0, 3) ?? [];
  const rest   = data?.rankings.slice(3)    ?? [];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">

      {/* ── top bar ── */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between sticky top-0 bg-gray-950/95 backdrop-blur z-10">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="text-gray-500 hover:text-white text-sm transition-colors flex items-center gap-1"
          >
            ← Map
          </Link>
          <div>
            <h1 className="text-white font-bold text-lg leading-none">
              🔥 UK Urban Hotspots
            </h1>
            <p className="text-gray-500 text-xs mt-0.5">
              Daily neighbourhood shame rankings
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {data && (
            <span className="text-gray-600 text-xs hidden sm:block">
              Updated {data.generated_at}
            </span>
          )}
          <div className="flex gap-1.5">
            {TIME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTimeRange(opt.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  timeRange === opt.value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">

        {/* ── loading / error ── */}
        {loading && (
          <div className="flex items-center justify-center h-64 text-gray-500 animate-pulse">
            Loading rankings...
          </div>
        )}
        {error && (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <p className="text-red-400">{error}</p>
            <button onClick={fetchRankings} className="px-4 py-2 bg-blue-600 rounded text-sm">
              Retry
            </button>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {/* ── stats bar ── */}
            <div className="grid grid-cols-3 gap-4 mb-10">
              <div className="bg-gray-900 rounded-xl p-4 text-center">
                <p className="text-3xl font-black text-white">{data.total_areas}</p>
                <p className="text-gray-500 text-xs mt-1">Areas Ranked</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-4 text-center">
                <p className="text-3xl font-black text-white">
                  {data.rankings.reduce((s, r) => s + r.event_count, 0).toLocaleString()}
                </p>
                <p className="text-gray-500 text-xs mt-1">Total Events</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-4 text-center">
                <p className="text-3xl font-black" style={{ color: "#ef4444" }}>
                  {top3[0]?.shame_score ?? "—"}
                </p>
                <p className="text-gray-500 text-xs mt-1">Worst Score</p>
              </div>
            </div>

            {/* ── podium ── */}
            {top3.length >= 3 && (
              <div className="mb-10">
                <p className="text-gray-500 text-xs uppercase tracking-widest font-semibold mb-6 text-center">
                  Top 3 Worst Areas
                </p>
                <div className="grid grid-cols-3 gap-6 items-end">
                  {/* Silver — 2nd */}
                  <PodiumCard area={top3[1]} position={2} />
                  {/* Gold — 1st (tallest) */}
                  <PodiumCard area={top3[0]} position={1} />
                  {/* Bronze — 3rd */}
                  <PodiumCard area={top3[2]} position={3} />
                </div>
              </div>
            )}

            {/* ── full leaderboard header ── */}
            {rest.length > 0 && (
              <div className="mb-2">
                <div
                  className="grid text-xs font-semibold uppercase tracking-wider text-gray-600 px-5 mb-1"
                  style={{ gridTemplateColumns: "2.5rem 1fr 9rem 10rem 5rem 7rem" }}
                >
                  <span>Rank</span>
                  <span>Area</span>
                  <span>Shame Score</span>
                  <span>Hazard Breakdown</span>
                  <span className="text-right">Volume</span>
                  <span className="text-right">Trend</span>
                </div>
                <div className="space-y-1">
                  {/* show top 3 in table too for continuity */}
                  {data.rankings.map((area) => (
                    <RankRow key={area.area} area={area} highlight={area.rank <= 3} />
                  ))}
                </div>
              </div>
            )}

            {/* ── empty state ── */}
            {data.rankings.length === 0 && (
              <div className="text-center py-20 text-gray-500">
                <p className="text-4xl mb-3">🎉</p>
                <p className="font-semibold text-white">No data for this period</p>
                <p className="text-sm mt-1">Try "All Time" to see historical rankings</p>
              </div>
            )}

            {/* ── most improved ── */}
            <MostImproved areas={data.most_improved} />

            {/* ── footer note ── */}
            <p className="text-gray-700 text-xs text-center mt-12">
              Shame Score = weighted severity × volume × hazard diversity.
              Sources: UK Police Street Crime API · Environment Agency Flood Monitor · BBC / Guardian RSS.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
