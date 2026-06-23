import { normalizeTeamName } from "./teamNames";
import type { FixtureStatus, FwcFixture } from "./fixtures";

const GAMMA_BASE = "https://gamma-api.polymarket.com";
const MATCH_SLUG_RE = /^fifwc-[a-z]+-[a-z]+-2026-\d{2}-\d{2}$/;

type GammaMarket = {
  groupItemTitle?: string;
  outcomePrices?: string | string[];
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

function priceToOdds(price: number | null): number | null {
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
  const now = Date.now();
  if (kickoff > now) return "upcoming";
  // Kickoff passed and markets still open — treat as live/in-play window.
  return "live";
}

function parseMoneylineEvent(event: GammaEvent): FwcFixture | null {
  const slug = event.slug ?? "";
  if (!MATCH_SLUG_RE.test(slug)) return null;

  const title = (event.title ?? "").trim();
  const teams = parseTeamsFromTitle(title);
  if (!teams) return null;

  const [home, away] = teams;
  const markets = event.markets ?? [];
  const kickoffUtc = parseKickoff(event, markets);
  const allClosed =
    Boolean(event.closed) || (markets.length > 0 && markets.every((m) => m.closed));

  let homeOdds: number | null = null;
  let drawOdds: number | null = null;
  let awayOdds: number | null = null;

  for (const market of markets) {
    const label = (market.groupItemTitle ?? "").trim();
    const odds = priceToOdds(yesPrice(market));
    if (!odds) continue;

    if (label.toLowerCase().startsWith("draw")) {
      drawOdds = odds;
      continue;
    }

    const normalized = normalizeTeamName(label);
    if (normalized === home) homeOdds = odds;
    else if (normalized === away) awayOdds = odds;
  }

  const status = fixtureStatus(kickoffUtc, allClosed);

  return {
    id: String(event.id ?? slug),
    slug,
    label: title,
    home,
    away,
    kickoffUtc,
    status,
    homeOdds,
    drawOdds,
    awayOdds,
    closed: allClosed,
  };
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
