/**
 * Live match-state feed from ESPN's public scoreboard (TS port of live_feed.py).
 *
 * No API key required. Parses an in-progress fixture into a {@link LiveMatch}
 * snapshot — score, elapsed minute, status, red cards — that maps onto the
 * in-play model's {@link LiveState}. Best-effort: returns null/[] on any
 * network or parse error. The pure helpers (parseScoreboardEvent, orientedTo)
 * take plain objects so they are unit-testable without the network.
 *
 * Network fetches here must run server-side (ESPN has no CORS headers).
 */

import type { LiveState } from "./live";
import { normalizeTeamName } from "./teamNames";

const ESPN_SCOREBOARD =
  "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard";
const ESPN_SUMMARY =
  "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary";
export const DEFAULT_LEAGUE = "fifa.world"; // FIFA World Cup
const MATCH_LENGTH = 90;

const NOISE_TOKENS = new Set(["vs", "fc", "afc", "national", "team"]);

export interface LiveMatch {
  eventId: string;
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  minute: number;
  statusState: string; // "pre" | "in" | "post"
  statusDetail: string; // e.g. "HT", "63'", "FT"
  statusName: string; // e.g. "STATUS_SECOND_HALF"
  homeTeamId: string;
  awayTeamId: string;
  redCardsHome: number;
  redCardsAway: number;
}

// --- Loose ESPN payload shapes (only the fields we read) ---------------------

type EspnTeam = {
  id?: string | number;
  displayName?: string;
  name?: string;
  shortDisplayName?: string;
};
type EspnCompetitor = {
  homeAway?: string;
  score?: string | number;
  team?: EspnTeam;
};
type EspnStatusType = {
  state?: string;
  name?: string;
  detail?: string;
  shortDetail?: string;
};
type EspnStatus = {
  clock?: number;
  displayClock?: string;
  type?: EspnStatusType;
};
type EspnCompetition = {
  status?: EspnStatus;
  competitors?: EspnCompetitor[];
};
export type EspnEvent = {
  id?: string | number;
  name?: string;
  status?: EspnStatus;
  competitions?: EspnCompetition[];
};
type EspnScoreboard = { events?: EspnEvent[] };
type EspnKeyEvent = { type?: { text?: string }; team?: { id?: string | number } };
type EspnSummary = { keyEvents?: EspnKeyEvent[] };

// --- Pure helpers ------------------------------------------------------------

function nameTokens(name: string): Set<string> {
  const normalized = normalizeTeamName(name).toLowerCase();
  const tokens = (normalized.match(/[a-z0-9]+/g) ?? []).filter(
    (t) => !NOISE_TOKENS.has(t),
  );
  return new Set(tokens);
}

function tokensMatch(a: Set<string>, b: Set<string>): boolean {
  if (a.size === 0 || b.size === 0) return false;
  const subset = (x: Set<string>, y: Set<string>) => [...x].every((t) => y.has(t));
  return subset(a, b) || subset(b, a);
}

function coerceInt(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

function teamName(competitor: EspnCompetitor): string {
  const team = competitor.team ?? {};
  return String(team.displayName ?? team.name ?? team.shortDisplayName ?? "");
}

function minuteFromStatus(status: EspnStatus, state: string): number {
  if (state === "pre") return 0;
  if (state === "post") return MATCH_LENGTH;
  const clock = status.clock;
  if (clock != null && Number.isFinite(Number(clock))) {
    return Math.min(Math.max(Number(clock) / 60, 0), MATCH_LENGTH);
  }
  // Fallback: leading digits of a display string like "63'" or "45'+2'".
  const detail = String(status.type?.detail ?? status.displayClock ?? "");
  const match = detail.match(/^\s*(\d+)/);
  if (match) return Math.min(Math.max(Number(match[1]), 0), MATCH_LENGTH);
  return 0;
}

/**
 * Parse one ESPN scoreboard event into a {@link LiveMatch}, oriented by ESPN's
 * own home/away flag. Use {@link orientedTo} to re-label to canonical names.
 */
export function parseScoreboardEvent(event: EspnEvent): LiveMatch | null {
  const comp = event.competitions?.[0];
  if (!comp) return null;

  const status = comp.status ?? event.status ?? {};
  const stype = status.type ?? {};
  const state = String(stype.state ?? "");
  const detail = String(stype.detail ?? stype.shortDetail ?? "");
  const name = String(stype.name ?? "");
  const minute = minuteFromStatus(status, state);

  const competitors = comp.competitors ?? [];
  let homeC = competitors.find((c) => c.homeAway === "home");
  let awayC = competitors.find((c) => c.homeAway === "away");
  if ((!homeC || !awayC) && competitors.length === 2) {
    [homeC, awayC] = competitors;
  }
  if (!homeC || !awayC) return null;

  return {
    eventId: String(event.id ?? ""),
    home: teamName(homeC),
    away: teamName(awayC),
    homeGoals: coerceInt(homeC.score),
    awayGoals: coerceInt(awayC.score),
    minute,
    statusState: state,
    statusDetail: detail,
    statusName: name,
    homeTeamId: String(homeC.team?.id ?? ""),
    awayTeamId: String(awayC.team?.id ?? ""),
    redCardsHome: 0,
    redCardsAway: 0,
  };
}

/**
 * Re-label a parsed match to `homeName`/`awayName` (matched by token overlap),
 * swapping goals/reds/ids if ESPN listed the teams the other way round. Returns
 * null if this event is not the requested fixture.
 */
export function orientedTo(
  match: LiveMatch,
  homeName: string,
  awayName: string,
): LiveMatch | null {
  const wantHome = nameTokens(homeName);
  const wantAway = nameTokens(awayName);
  const haveHome = nameTokens(match.home);
  const haveAway = nameTokens(match.away);

  if (tokensMatch(wantHome, haveHome) && tokensMatch(wantAway, haveAway)) {
    return { ...match, home: homeName, away: awayName };
  }
  if (tokensMatch(wantHome, haveAway) && tokensMatch(wantAway, haveHome)) {
    return {
      ...match,
      home: homeName,
      away: awayName,
      homeGoals: match.awayGoals,
      awayGoals: match.homeGoals,
      redCardsHome: match.redCardsAway,
      redCardsAway: match.redCardsHome,
      homeTeamId: match.awayTeamId,
      awayTeamId: match.homeTeamId,
    };
  }
  return null;
}

export function liveMatchToState(match: LiveMatch): LiveState {
  return {
    minute: match.minute,
    homeGoals: match.homeGoals,
    awayGoals: match.awayGoals,
    redCardsHome: match.redCardsHome,
    redCardsAway: match.redCardsAway,
    matchLength: MATCH_LENGTH,
  };
}

export function isLive(match: LiveMatch): boolean {
  return match.statusState === "in";
}

export function isFinal(match: LiveMatch): boolean {
  return match.statusState === "post";
}

// --- Network -----------------------------------------------------------------

async function fetchEvents(league: string): Promise<EspnEvent[]> {
  try {
    const res = await fetch(ESPN_SCOREBOARD.replace("{league}", league), {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = (await res.json()) as EspnScoreboard;
    return data.events ?? [];
  } catch {
    return [];
  }
}

async function fetchRedCards(
  league: string,
  eventId: string,
  homeTeamId: string,
  awayTeamId: string,
): Promise<[number, number]> {
  if (!eventId) return [0, 0];
  try {
    const url = new URL(ESPN_SUMMARY.replace("{league}", league));
    url.searchParams.set("event", eventId);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return [0, 0];
    const data = (await res.json()) as EspnSummary;
    let home = 0;
    let away = 0;
    for (const ke of data.keyEvents ?? []) {
      const text = String(ke.type?.text ?? "").toLowerCase();
      if (!text.includes("red card")) continue;
      const tid = String(ke.team?.id ?? "");
      if (tid && tid === homeTeamId) home += 1;
      else if (tid && tid === awayTeamId) away += 1;
    }
    return [home, away];
  } catch {
    return [0, 0];
  }
}

/**
 * Find the ESPN fixture for `homeName` vs `awayName` in `league`, oriented to
 * the requested names with red cards filled in when in play or finished.
 * Returns null if the fixture is not on the scoreboard or the feed is down.
 */
export async function findLiveMatch(
  homeName: string,
  awayName: string,
  league: string = DEFAULT_LEAGUE,
  options: { fetchCards?: boolean } = {},
): Promise<LiveMatch | null> {
  const { fetchCards = true } = options;
  for (const event of await fetchEvents(league)) {
    const parsed = parseScoreboardEvent(event);
    if (!parsed) continue;
    const match = orientedTo(parsed, homeName, awayName);
    if (!match) continue;
    if (fetchCards && (match.statusState === "in" || match.statusState === "post")) {
      const [redCardsHome, redCardsAway] = await fetchRedCards(
        league,
        match.eventId,
        match.homeTeamId,
        match.awayTeamId,
      );
      return { ...match, redCardsHome, redCardsAway };
    }
    return match;
  }
  return null;
}
