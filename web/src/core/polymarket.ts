import { normalizeTeamName } from "./teamNames";
import type { FixtureStatus, FwcFixture } from "./fixtures";
import type {
  BttsMarket,
  CorrectScoreMarket,
  SiblingMarkets,
  TotalsMarket,
} from "./markets";

const GAMMA_BASE = "https://gamma-api.polymarket.com";
const MATCH_SLUG_RE = /^fifwc-[a-z]+-[a-z]+-2026-\d{2}-\d{2}$/;

export type {
  BttsMarket,
  CorrectScoreMarket,
  SiblingMarkets,
  TotalsMarket,
} from "./markets";

type GammaMarket = {
  groupItemTitle?: string;
  sportsMarketType?: string;
  question?: string;
  slug?: string;
  outcomePrices?: string | string[];
  outcomes?: string | string[];
  closed?: boolean;
  gameStartTime?: string;
};

type GammaEvent = {
  id?: string | number;
  slug?: string;
  title?: string;
  endDate?: string;
  closed?: boolean;
  markets?: GammaMarket[];
};

function parseJsonArray<T>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      return Array.isArray(parsed) ? (parsed as T[]) : [];
    } catch {
      return [];
    }
  }
  return [];
}

function parseTeamsFromTitle(title: string): [string, string] | null {
  const parts = title.split(/\s+vs\.?\s+/i);
  if (parts.length !== 2) return null;
  return [normalizeTeamName(parts[0]), normalizeTeamName(parts[1])];
}

function yesPrice(market: GammaMarket): number | null {
  const prices = parseJsonArray<string>(market.outcomePrices);
  if (!prices.length) return null;
  const price = Number(prices[0]);
  return Number.isFinite(price) && price > 0 ? price : null;
}

function noPrice(market: GammaMarket): number | null {
  const prices = parseJsonArray<string>(market.outcomePrices);
  if (prices.length < 2) return null;
  const price = Number(prices[1]);
  return Number.isFinite(price) && price > 0 ? price : null;
}

export function priceToOdds(price: number | null): number | null {
  if (price == null || price <= 0) return null;
  const odds = 1 / price;
  return Number.isFinite(odds) && odds > 1 ? Number(odds.toFixed(3)) : null;
}

function parseKickoff(event: GammaEvent, markets: GammaMarket[]): string {
  for (const market of markets) {
    if (market.gameStartTime) {
      const parsed = new Date(market.gameStartTime.replace(" ", "T"));
      if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
    }
  }
  if (event.endDate) {
    const parsed = new Date(event.endDate);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
  }
  return "";
}

function fixtureStatus(kickoffUtc: string, closed: boolean): FixtureStatus {
  if (closed) return "finished";
  const kickoff = new Date(kickoffUtc).getTime();
  if (!kickoffUtc || Number.isNaN(kickoff)) return "upcoming";
  if (kickoff > Date.now()) return "upcoming";
  return "live";
}

const OU_LINE_RE = /o\/u\s+(\d+(?:\.\d+)?)/i;
const SCORE_IN_LABEL_RE = /(\d+)\s*[-–]\s*(\d+)/;

function parseTotalsLabel(label: string, question: string): number | null {
  const hay = `${label} ${question}`;
  const match = hay.match(OU_LINE_RE);
  if (!match) return null;
  const line = Number(match[1]);
  return Number.isFinite(line) ? line : null;
}

function isMatchTotal(label: string, question: string): boolean {
  const hay = `${label} ${question}`.toLowerCase();
  if (hay.includes("1h") || hay.includes("first half")) return false;
  if (hay.includes("team total")) return false;
  return hay.includes("o/u") || hay.includes("over") || hay.includes("under");
}

function parseBttsMarket(market: GammaMarket): BttsMarket | null {
  const hay = `${market.groupItemTitle ?? ""} ${market.question ?? ""}`.toLowerCase();
  if (!hay.includes("both teams") && !hay.includes("btts")) return null;
  return {
    yesOdds: priceToOdds(yesPrice(market)),
    noOdds: priceToOdds(noPrice(market)),
  };
}

function parseCorrectScoreMarket(market: GammaMarket): CorrectScoreMarket | null {
  const hay = `${market.groupItemTitle ?? ""} ${market.question ?? ""}`;
  const match = hay.match(SCORE_IN_LABEL_RE);
  if (!match) return null;
  const homeGoals = Number(match[1]);
  const awayGoals = Number(match[2]);
  if (!Number.isFinite(homeGoals) || !Number.isFinite(awayGoals)) return null;
  if (homeGoals > 10 || awayGoals > 10) return null;
  return {
    homeGoals,
    awayGoals,
    odds: priceToOdds(yesPrice(market)),
  };
}

/** Parse all market types from a Gamma event payload. */
export function parseSiblingMarkets(event: GammaEvent): SiblingMarkets | null {
  const slug = event.slug ?? "";
  if (!MATCH_SLUG_RE.test(slug)) return null;

  const title = (event.title ?? "").trim();
  const teams = parseTeamsFromTitle(title);
  if (!teams) return null;

  const [home, away] = teams;
  const markets = event.markets ?? [];

  let homeOdds: number | null = null;
  let drawOdds: number | null = null;
  let awayOdds: number | null = null;
  const totalsMap = new Map<number, TotalsMarket>();
  let btts: BttsMarket | null = null;
  const correctScores: CorrectScoreMarket[] = [];

  for (const market of markets) {
    const label = (market.groupItemTitle ?? "").trim();
    const question = market.question ?? "";
    const odds = priceToOdds(yesPrice(market));

    if (label.toLowerCase().startsWith("draw")) {
      drawOdds = odds;
      continue;
    }

    const normalized = normalizeTeamName(label);
    if (normalized === home) {
      homeOdds = odds;
      continue;
    }
    if (normalized === away) {
      awayOdds = odds;
      continue;
    }

    if (isMatchTotal(label, question)) {
      const line = parseTotalsLabel(label, question);
      if (line != null) {
        const existing = totalsMap.get(line) ?? {
          line,
          overOdds: null,
          underOdds: null,
        };
        const hay = `${label} ${question}`.toLowerCase();
        const yes = priceToOdds(yesPrice(market));
        const no = priceToOdds(noPrice(market));
        if (hay.includes("over")) existing.overOdds = yes;
        else if (hay.includes("under")) existing.underOdds = yes;
        else {
          if (yes) existing.overOdds = yes;
          if (no) existing.underOdds = no;
        }
        totalsMap.set(line, existing);
      }
      continue;
    }

    const bttsParsed = parseBttsMarket(market);
    if (bttsParsed) {
      btts = bttsParsed;
      continue;
    }

    const cs = parseCorrectScoreMarket(market);
    if (cs) correctScores.push(cs);
  }

  return {
    eventSlug: slug,
    home,
    away,
    homeOdds,
    drawOdds,
    awayOdds,
    totals: [...totalsMap.values()].sort((a, b) => a.line - b.line),
    btts,
    correctScores,
  };
}

function parseMoneylineEvent(event: GammaEvent): FwcFixture | null {
  const siblings = parseSiblingMarkets(event);
  if (!siblings) return null;

  const markets = event.markets ?? [];
  const kickoffUtc = parseKickoff(event, markets);
  const allClosed =
    Boolean(event.closed) || (markets.length > 0 && markets.every((m) => m.closed));
  const status = fixtureStatus(kickoffUtc, allClosed);

  return {
    id: String(event.id ?? siblings.eventSlug),
    slug: siblings.eventSlug,
    label: (event.title ?? "").trim(),
    home: siblings.home,
    away: siblings.away,
    kickoffUtc,
    status,
    homeOdds: siblings.homeOdds,
    drawOdds: siblings.drawOdds,
    awayOdds: siblings.awayOdds,
    closed: allClosed,
    siblings,
  };
}

async function fetchGammaEvent(slug: string): Promise<GammaEvent | null> {
  const response = await fetch(`${GAMMA_BASE}/events/slug/${slug}`, {
    next: { revalidate: 60 },
  });
  if (!response.ok) return null;
  return (await response.json()) as GammaEvent;
}

/** Fetch one match event and parse moneyline + sibling prop markets. */
export async function fetchSiblingMarkets(slug: string): Promise<SiblingMarkets | null> {
  const event = await fetchGammaEvent(slug);
  if (!event) return null;
  return parseSiblingMarkets(event);
}

export async function fetchFwcFixtures(limit = 150): Promise<FwcFixture[]> {
  const url = new URL("/events", GAMMA_BASE);
  url.searchParams.set("tag_slug", "fifa-world-cup");
  url.searchParams.set("closed", "false");
  url.searchParams.set("limit", String(limit));

  const response = await fetch(url.toString(), {
    next: { revalidate: 60 },
  });
  if (!response.ok) {
    throw new Error(`Gamma API error: ${response.status}`);
  }

  const payload = (await response.json()) as unknown;
  if (!Array.isArray(payload)) return [];

  const fixtures = payload
    .map((row) => parseMoneylineEvent(row as GammaEvent))
    .filter((fixture): fixture is FwcFixture => fixture != null);

  fixtures.sort(
    (a, b) => new Date(a.kickoffUtc).getTime() - new Date(b.kickoffUtc).getTime(),
  );

  return fixtures;
}
