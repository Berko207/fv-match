/** Polymarket sports WebSocket feed (wss://sports-api.polymarket.com/ws). */

export const POLY_SPORTS_WS = "wss://sports-api.polymarket.com/ws";

export interface PolySportUpdate {
  gameId: number | null;
  leagueAbbreviation: string;
  slug: string;
  homeTeam: string;
  awayTeam: string;
  status: string;
  score: string;
  period: string;
  elapsed: string;
  live: boolean;
  ended: boolean;
  turn?: string;
  finishedTimestamp?: string;
  receivedAt: string;
}

export function parsePolySportMessage(raw: string): PolySportUpdate | null {
  if (raw === "ping" || raw === "pong") return null;
  try {
    const data = JSON.parse(raw) as Record<string, unknown>;
    const slug = String(data.slug ?? "").trim();
    if (!slug) return null;
    return {
      gameId: typeof data.gameId === "number" ? data.gameId : null,
      leagueAbbreviation: String(data.leagueAbbreviation ?? ""),
      slug,
      homeTeam: String(data.homeTeam ?? ""),
      awayTeam: String(data.awayTeam ?? ""),
      status: String(data.status ?? ""),
      score: String(data.score ?? ""),
      period: String(data.period ?? ""),
      elapsed: String(data.elapsed ?? ""),
      live: Boolean(data.live),
      ended: Boolean(data.ended),
      turn: data.turn != null ? String(data.turn) : undefined,
      finishedTimestamp:
        data.finished_timestamp != null ? String(data.finished_timestamp) : undefined,
      receivedAt: new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

export function formatSportUpdateLine(update: PolySportUpdate): string {
  const liveTag = update.live ? "LIVE" : update.ended ? "FT" : update.status;
  const clock = [update.period, update.elapsed].filter(Boolean).join(" · ");
  const teams = [update.homeTeam, update.awayTeam].filter(Boolean).join(" vs ");
  return `[${liveTag}] ${teams || update.slug} ${update.score}${clock ? ` (${clock})` : ""}`;
}
