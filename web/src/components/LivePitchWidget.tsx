"use client";

import type { PolySportUpdate } from "@/core/polySportsFeed";
import type { PolyLiveState } from "@/core/marketCatalog";

type LiveSnapshot = PolySportUpdate | PolyLiveState;

function parseScore(score: string): [string, string] {
  const parts = score.split("-").map((s) => s.trim());
  if (parts.length === 2) return [parts[0], parts[1]];
  return ["0", "0"];
}

function attackingSide(
  turn: string | undefined,
  homeAbbrev: string,
  awayAbbrev: string,
  homeTeam: string,
  awayTeam: string,
): "home" | "away" | null {
  if (!turn) return null;
  const t = turn.toLowerCase();
  if (
    t === homeAbbrev.toLowerCase() ||
    t.includes(homeTeam.toLowerCase()) ||
    t.includes("home")
  ) {
    return "home";
  }
  if (
    t === awayAbbrev.toLowerCase() ||
    t.includes(awayTeam.toLowerCase()) ||
    t.includes("away")
  ) {
    return "away";
  }
  return null;
}

export function LivePitchWidget({
  homeTeam,
  awayTeam,
  homeAbbrev = "",
  awayAbbrev = "",
  live,
}: {
  homeTeam: string;
  awayTeam: string;
  homeAbbrev?: string;
  awayAbbrev?: string;
  live: LiveSnapshot | null;
}) {
  const score = live?.score ?? "0-0";
  const [homeGoals, awayGoals] = parseScore(score);
  const period = live?.period ?? "";
  const elapsed = live?.elapsed ?? "";
  const clock = [period, elapsed ? `${elapsed}'` : ""].filter(Boolean).join(" · ");
  const isLive = live && "live" in live ? live.live : Boolean(live);
  const turn = live && "turn" in live ? live.turn : undefined;
  const attack = attackingSide(turn, homeAbbrev, awayAbbrev, homeTeam, awayTeam);
  const ballX = attack === "home" ? "22%" : attack === "away" ? "78%" : "50%";
  const attackLabel =
    attack === "home"
      ? `${homeTeam} attacking`
      : attack === "away"
        ? `${awayTeam} attacking`
        : isLive
          ? "Live stats"
          : "Match center";

  return (
    <div className="overflow-hidden rounded-xl border border-emerald-500/20 bg-gradient-to-b from-emerald-950/80 to-emerald-900/40">
      <div className="flex items-center justify-between border-b border-emerald-500/15 px-3 py-2 text-xs">
        <span className="inline-flex items-center gap-1.5 font-semibold uppercase tracking-wide text-emerald-200">
          {isLive ? (
            <>
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-400" />
              Live
            </>
          ) : (
            "Match"
          )}
        </span>
        <span className="font-mono text-emerald-100/80">{clock || "—"}</span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 py-3">
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wide text-emerald-200/70">
            {homeAbbrev || "HOME"}
          </p>
          <p className="truncate text-sm font-semibold text-white">{homeTeam}</p>
        </div>
        <div className="min-w-[4.5rem] text-center font-mono text-2xl font-bold text-white">
          {homeGoals}
          <span className="mx-1 text-emerald-300/60">:</span>
          {awayGoals}
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wide text-emerald-200/70">
            {awayAbbrev || "AWAY"}
          </p>
          <p className="truncate text-sm font-semibold text-white">{awayTeam}</p>
        </div>
      </div>

      <div className="relative mx-3 mb-3 aspect-[16/9] overflow-hidden rounded-lg border border-emerald-400/20 bg-[linear-gradient(180deg,#1a6b3c_0%,#145a32_45%,#1a6b3c_100%)]">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-white/50" />
          <div className="absolute left-1/2 top-1/2 h-[28%] w-[28%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/50" />
          <div className="absolute left-0 top-1/2 h-[55%] w-[18%] -translate-y-1/2 border border-white/40 border-l-0" />
          <div className="absolute right-0 top-1/2 h-[55%] w-[18%] -translate-y-1/2 border border-white/40 border-r-0" />
        </div>

        <div
          className="absolute top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 transition-all duration-[1.8s] ease-out"
          style={{ left: ballX }}
        >
          <span className="text-xl drop-shadow-[0_2px_6px_rgba(0,0,0,0.55)]">⚽</span>
        </div>

        <div className="absolute bottom-2 right-2 rounded-md bg-black/45 px-2 py-1 text-[10px] font-medium text-emerald-100">
          {attackLabel}
        </div>
      </div>

      <p className="border-t border-emerald-500/10 px-3 py-2 text-[11px] text-emerald-100/60">
        Live stats from Polymarket&apos;s sports feed — not a TV broadcast. Watch the
        match on FOX, FS1, Telemundo, or your local rights holder.
      </p>
    </div>
  );
}
