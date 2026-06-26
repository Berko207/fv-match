import {
  matchBaseSlug,
  parseGammaEvent,
  type CatalogEvent,
  type CatalogMarket,
  type PolyLiveState,
} from "./marketCatalog";

const GAMMA_BASE = "https://gamma-api.polymarket.com";

/** Known fifwc sibling event suffixes (discovered from Polymarket slug patterns). */
export const FWC_EVENT_SUFFIXES = [
  "",
  "-more-markets",
  "-exact-score",
  "-halftime-result",
  "-second-half-result",
  "-first-to-score",
  "-total-corners",
  "-player-props",
] as const;

export type MatchTab =
  | "game-lines"
  | "exact-score"
  | "halves"
  | "corners"
  | "goals"
  | "assists"
  | "shots";

export interface MoneylineQuote {
  home: CatalogMarket | null;
  draw: CatalogMarket | null;
  away: CatalogMarket | null;
  homePct: number | null;
  drawPct: number | null;
  awayPct: number | null;
}

export interface MatchSurface {
  baseSlug: string;
  title: string;
  home: string;
  away: string;
  subEvents: CatalogEvent[];
  marketCount: number;
  liveState: PolyLiveState | null;
  moneyline: MoneylineQuote;
  tabs: Record<MatchTab, CatalogMarket[]>;
  fetchedAt: string;
}

type GammaEvent = Record<string, unknown>;

async function fetchGammaEventRaw(slug: string): Promise<GammaEvent | null> {
  const response = await fetch(`${GAMMA_BASE}/events/slug/${slug}`, {
    cache: "no-store",
  });
  if (!response.ok) return null;
  return (await response.json()) as GammaEvent;
}

function parseTeamsFromTitle(title: string): [string, string] | null {
  const parts = title.split(/\s+vs\.?\s+/i);
  if (parts.length !== 2) return null;
  const home = parts[0].trim();
  const away = parts[1].replace(/\s+-\s+.+$/i, "").trim();
  return home && away ? [home, away] : null;
}

function normalizeTeam(label: string, home: string, away: string): "home" | "draw" | "away" | null {
  const l = label.toLowerCase();
  if (l.includes("draw")) return "draw";
  if (l === home.toLowerCase() || label === home) return "home";
  if (l === away.toLowerCase() || label === away) return "away";
  return null;
}

export function extractMoneyline(
  subEvents: CatalogEvent[],
  home: string,
  away: string,
): MoneylineQuote {
  const main = subEvents.find((e) => e.slug === e.matchBaseSlug) ?? subEvents[0];
  let homeM: CatalogMarket | null = null;
  let drawM: CatalogMarket | null = null;
  let awayM: CatalogMarket | null = null;

  for (const market of main?.markets ?? []) {
    const label = market.groupTitle || market.question;
    const side = normalizeTeam(label, home, away);
    if (side === "home" && !homeM) homeM = market;
    if (side === "draw" && !drawM) drawM = market;
    if (side === "away" && !awayM) awayM = market;
  }

  const pct = (m: CatalogMarket | null) =>
    m?.yesPrice != null ? m.yesPrice * 100 : null;

  return {
    home: homeM,
    draw: drawM,
    away: awayM,
    homePct: pct(homeM),
    drawPct: pct(drawM),
    awayPct: pct(awayM),
  };
}

const GAME_LINE_TYPES = new Set([
  "moneyline",
  "spreads",
  "totals",
  "both_teams_to_score",
  "both_teams_to_score_first_half",
  "both_teams_to_score_second_half",
  "soccer_team_totals",
  "soccer_first_half_team_totals",
  "soccer_second_half_team_totals",
  "first_half_totals",
  "second_half_totals",
]);

const HALVES_TYPES = new Set([
  "first_half_moneyline",
  "second_half_moneyline",
  "first_half_totals",
  "second_half_totals",
  "both_teams_to_score_first_half",
  "both_teams_to_score_second_half",
  "soccer_first_half_team_totals",
  "soccer_second_half_team_totals",
]);

function isExactScoreMarket(m: CatalogMarket): boolean {
  return /\d+\s*[-–]\s*\d+/.test(`${m.groupTitle} ${m.question}`);
}

export function classifyMarketsToTabs(
  subEvents: CatalogEvent[],
  baseSlug: string,
): Record<MatchTab, CatalogMarket[]> {
  const tabs: Record<MatchTab, CatalogMarket[]> = {
    "game-lines": [],
    "exact-score": [],
    halves: [],
    corners: [],
    goals: [],
    assists: [],
    shots: [],
  };

  for (const event of subEvents) {
    const suffix = event.slug.slice(baseSlug.length);

    if (suffix === "-exact-score") {
      tabs["exact-score"].push(...event.markets);
      continue;
    }
    if (suffix === "-total-corners") {
      tabs.corners.push(...event.markets);
      continue;
    }
    if (suffix === "-halftime-result" || suffix === "-second-half-result") {
      tabs.halves.push(...event.markets);
      continue;
    }
    if (suffix === "-first-to-score") {
      tabs["game-lines"].push(...event.markets);
      continue;
    }
    if (suffix === "-player-props") {
      for (const m of event.markets) {
        const t = m.sportsMarketType;
        if (t === "soccer_player_goals" || t === "soccer_player_goals_plus_assists") {
          tabs.goals.push(m);
        } else if (t === "soccer_player_assists") {
          tabs.assists.push(m);
        } else if (
          t === "soccer_player_shots" ||
          t === "soccer_player_shots_on_target"
        ) {
          tabs.shots.push(m);
        }
      }
      continue;
    }

    for (const m of event.markets) {
      const t = m.sportsMarketType;
      if (suffix === "" && t === "moneyline") {
        tabs["game-lines"].push(m);
      } else if (suffix === "-more-markets") {
        if (HALVES_TYPES.has(t)) tabs.halves.push(m);
        else if (GAME_LINE_TYPES.has(t)) tabs["game-lines"].push(m);
        else if (isExactScoreMarket(m)) tabs["exact-score"].push(m);
      } else if (isExactScoreMarket(m)) {
        tabs["exact-score"].push(m);
      }
    }
  }

  return tabs;
}

export async function fetchMatchSurface(baseSlug: string): Promise<MatchSurface | null> {
  const base = matchBaseSlug(baseSlug) ?? baseSlug;
  if (!base.startsWith("fifwc-")) return null;

  const slugs = FWC_EVENT_SUFFIXES.map((suffix) => `${base}${suffix}`);
  const rawEvents = await Promise.all(slugs.map(fetchGammaEventRaw));

  const subEvents: CatalogEvent[] = [];
  for (const raw of rawEvents) {
    if (!raw || typeof raw.slug !== "string") continue;
    const parsed = parseGammaEvent(raw as Parameters<typeof parseGammaEvent>[0], "fifa-world-cup");
    if (parsed) subEvents.push(parsed);
  }

  if (!subEvents.length) return null;

  const main =
    subEvents.find((e) => e.slug === base) ??
    subEvents.find((e) => e.subEventLabel === "Match result") ??
    subEvents[0];
  const teams = parseTeamsFromTitle(main.title);
  const home = teams?.[0] ?? "";
  const away = teams?.[1] ?? "";
  const title = teams ? `${teams[0]} vs. ${teams[1]}` : main.title;

  const liveState =
    subEvents.find((e) => e.liveState?.live)?.liveState ??
    subEvents.find((e) => e.liveState)?.liveState ??
    null;

  const tabs = classifyMarketsToTabs(subEvents, base);
  const marketCount = subEvents.reduce((n, e) => n + e.marketCount, 0);

  return {
    baseSlug: base,
    title,
    home,
    away,
    subEvents,
    marketCount,
    liveState,
    moneyline: extractMoneyline(subEvents, home, away),
    tabs,
    fetchedAt: new Date().toISOString(),
  };
}
