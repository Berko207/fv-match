import { priceToOdds } from "./polymarket";

const GAMMA_BASE = "https://gamma-api.polymarket.com";

/** Sports tags we pull for the full Polymarket catalog. */
export const POLYMARKET_SPORTS_TAGS = [
  "fifa-world-cup",
  "mlb",
  "nba",
  "nfl",
  "soccer",
  "ucl",
  "tennis",
  "golf",
] as const;

export type PolyCategory = (typeof POLYMARKET_SPORTS_TAGS)[number] | "other";

export type ByrealCategory = "football" | "basketball" | "baseball" | "other";

export type CatalogStatus = "upcoming" | "live" | "finished";

/** Live scoreboard fields from Gamma (same source as Polymarket's match widget). */
export interface PolyLiveState {
  live: boolean;
  ended: boolean;
  score: string;
  period: string;
  elapsed: string;
  homeTeam: string;
  awayTeam: string;
  homeAbbrev: string;
  awayAbbrev: string;
}

export interface CatalogMarket {
  id: string;
  slug: string;
  question: string;
  groupTitle: string;
  yesPrice: number | null;
  noPrice: number | null;
  yesOdds: number | null;
  noOdds: number | null;
  liquidity: number | null;
  closed: boolean;
  sportsMarketType: string;
  comboStatus: string;
}

export interface CatalogEvent {
  id: string;
  slug: string;
  title: string;
  description: string;
  category: string;
  status: CatalogStatus;
  kickoffUtc: string;
  liquidity: number | null;
  volume24h: number | null;
  closed: boolean;
  marketCount: number;
  markets: CatalogMarket[];
  polymarketUrl: string;
  byrealUrl: string | null;
  gameId: number | null;
  matchBaseSlug: string | null;
  subEventLabel: string;
  liveState: PolyLiveState | null;
}

/** One World Cup fixture — main moneyline + sibling prop events merged for browsing. */
export interface CatalogMatch {
  baseSlug: string;
  title: string;
  home: string;
  away: string;
  category: string;
  status: CatalogStatus;
  kickoffUtc: string;
  liquidity: number | null;
  volume24h: number | null;
  closed: boolean;
  marketCount: number;
  subEventCount: number;
  subEvents: CatalogEvent[];
  liveState: PolyLiveState | null;
  polymarketUrl: string;
  byrealUrl: string | null;
}

export interface VenueCatalog {
  venue: "polymarket" | "byreal";
  label: string;
  tagline: string;
  accent: "emerald" | "amber";
  fetchedAt: string;
  stats: {
    events: number;
    markets: number;
    openEvents: number;
    categories: Record<string, number>;
    matches: number;
  };
  events: CatalogEvent[];
  matches: CatalogMatch[];
}

export interface MarketsCatalogResponse {
  polymarket: VenueCatalog;
  byreal: VenueCatalog;
  fetchedAt: string;
}

type GammaMarket = {
  id?: string | number;
  groupItemTitle?: string;
  question?: string;
  slug?: string;
  outcomePrices?: string | string[];
  outcomes?: string | string[];
  closed?: boolean;
  gameStartTime?: string;
  liquidity?: string | number;
  liquidityClob?: string | number;
  sportsMarketType?: string;
  comboStatus?: string;
};

type GammaTeam = {
  name?: string;
  abbreviation?: string;
  ordering?: string;
};

type GammaEvent = {
  id?: string | number;
  slug?: string;
  title?: string;
  description?: string;
  endDate?: string;
  closed?: boolean;
  liquidity?: number;
  volume24hr?: number;
  markets?: GammaMarket[];
  gameId?: number;
  live?: boolean;
  ended?: boolean;
  score?: string;
  period?: string;
  elapsed?: string;
  teams?: GammaTeam[];
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

function parseNum(value: unknown): number | null {
  if (value == null) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
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

const FWC_MATCH_BASE_RE = /^(fifwc-[a-z]+-[a-z]+-\d{4}-\d{2}-\d{2})/;

export function matchBaseSlug(slug: string): string | null {
  const match = slug.match(FWC_MATCH_BASE_RE);
  return match?.[1] ?? null;
}

function parseTeamsFromTitle(title: string): [string, string] | null {
  const parts = title.split(/\s+vs\.?\s+/i);
  if (parts.length !== 2) return null;
  const home = parts[0].trim();
  const away = parts[1].replace(/\s+-\s+.+$/i, "").trim();
  if (!home || !away) return null;
  return [home, away];
}

function subEventLabel(slug: string, baseSlug: string | null): string {
  if (!baseSlug || slug === baseSlug) return "Match result";
  const suffix = slug.slice(baseSlug.length).replace(/^-/, "");
  if (!suffix) return "Match result";
  return suffix
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function parseLiveState(event: GammaEvent): PolyLiveState | null {
  const teams = event.teams ?? [];
  const home = teams.find((t) => t.ordering === "home") ?? teams[0];
  const away = teams.find((t) => t.ordering === "away") ?? teams[1];
  const hasSignal =
    event.live ||
    event.ended ||
    event.score ||
    event.period ||
    event.elapsed;
  if (!hasSignal && !home?.name && !away?.name) return null;

  return {
    live: Boolean(event.live),
    ended: Boolean(event.ended),
    score: String(event.score ?? ""),
    period: String(event.period ?? ""),
    elapsed: String(event.elapsed ?? ""),
    homeTeam: home?.name ?? "",
    awayTeam: away?.name ?? "",
    homeAbbrev: home?.abbreviation ?? "",
    awayAbbrev: away?.abbreviation ?? "",
  };
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

function catalogStatus(
  kickoffUtc: string,
  closed: boolean,
  liveState: PolyLiveState | null,
): CatalogStatus {
  if (closed || liveState?.ended) return "finished";
  if (liveState?.live) return "live";
  const kickoff = new Date(kickoffUtc).getTime();
  if (!kickoffUtc || Number.isNaN(kickoff)) return "upcoming";
  if (kickoff > Date.now()) return "upcoming";
  return "live";
}

function parseCatalogMarket(market: GammaMarket): CatalogMarket {
  const yes = yesPrice(market);
  const no = noPrice(market);
  const liquidity =
    parseNum(market.liquidityClob) ?? parseNum(market.liquidity);

  return {
    id: String(market.id ?? market.slug ?? market.question ?? ""),
    slug: market.slug ?? "",
    question: (market.question ?? "").trim(),
    groupTitle: (market.groupItemTitle ?? "").trim(),
    yesPrice: yes,
    noPrice: no,
    yesOdds: priceToOdds(yes),
    noOdds: priceToOdds(no),
    liquidity,
    closed: Boolean(market.closed),
    sportsMarketType: (market.sportsMarketType ?? "").trim(),
    comboStatus: (market.comboStatus ?? "").trim(),
  };
}

function inferPolyCategory(slug: string, sourceTag: string): string {
  if (slug.startsWith("fifwc-") || slug.includes("world-cup")) return "fifa-world-cup";
  if (slug.startsWith("mlb-") || sourceTag === "mlb") return "mlb";
  if (slug.startsWith("nba-") || sourceTag === "nba") return "nba";
  if (slug.startsWith("nfl-") || sourceTag === "nfl") return "nfl";
  if (sourceTag === "ucl" || slug.includes("champions-league")) return "ucl";
  if (sourceTag === "soccer" || slug.includes("epl")) return "soccer";
  if (sourceTag === "tennis") return "tennis";
  if (sourceTag === "golf") return "golf";
  return sourceTag || "other";
}

function byrealUrlForEvent(slug: string): string | null {
  if (!slug) return null;
  return `https://www.byreal.io/en/predict?event=${encodeURIComponent(slug)}`;
}

export function parseGammaEvent(
  event: GammaEvent,
  sourceTag: string,
): CatalogEvent | null {
  const slug = (event.slug ?? "").trim();
  const title = (event.title ?? "").trim();
  if (!slug || !title) return null;

  const markets = (event.markets ?? []).map(parseCatalogMarket);
  const kickoffUtc = parseKickoff(event, event.markets ?? []);
  const allClosed =
    Boolean(event.closed) ||
    (markets.length > 0 && markets.every((m) => m.closed));
  const base = matchBaseSlug(slug);
  const liveState = parseLiveState(event);

  return {
    id: String(event.id ?? slug),
    slug,
    title,
    description: (event.description ?? "").trim(),
    category: inferPolyCategory(slug, sourceTag),
    status: catalogStatus(kickoffUtc, allClosed, liveState),
    kickoffUtc,
    liquidity: parseNum(event.liquidity),
    volume24h: parseNum(event.volume24hr),
    closed: allClosed,
    marketCount: markets.length,
    markets,
    polymarketUrl: `https://polymarket.com/event/${slug}`,
    byrealUrl: isByrealCurated(slug, title) ? byrealUrlForEvent(slug) : null,
    gameId: typeof event.gameId === "number" ? event.gameId : null,
    matchBaseSlug: base,
    subEventLabel: subEventLabel(slug, base),
    liveState,
  };
}

/** Byreal Predict launch categories (Polymarket liquidity, Byreal front-end). */
export function isByrealCurated(slug: string, title = ""): boolean {
  const s = slug.toLowerCase();
  const t = title.toLowerCase();

  if (s.startsWith("fifwc-")) return true;
  if (s.includes("world-cup") && (s.includes("winner") || s.includes("group")))
    return true;

  if (s.startsWith("mlb-") && /\d{4}-\d{2}-\d{2}$/.test(s)) return true;
  if (s.startsWith("mlb-") && t.includes(" vs")) return true;

  if (t.includes("nba finals")) return true;
  if (s.includes("nba-finals")) return true;
  if (s === "2026-nba-champion" || s.includes("nba-champion")) return true;
  if (s.includes("nba-playoffs-finals")) return true;

  return false;
}

export function byrealCategory(slug: string, title = ""): ByrealCategory {
  const s = slug.toLowerCase();
  const t = title.toLowerCase();
  if (s.startsWith("fifwc-") || s.includes("world-cup")) return "football";
  if (s.startsWith("mlb-") || t.includes("mlb")) return "baseball";
  if (t.includes("nba") || s.includes("nba")) return "basketball";
  return "other";
}

const GAMMA_PAGE_SIZE = 100;

async function fetchGammaEventsPage(params: Record<string, string>): Promise<GammaEvent[]> {
  const url = new URL("/events", GAMMA_BASE);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, value);
  }

  const response = await fetch(url.toString(), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Gamma ${params.tag_slug ?? params.series_slug ?? "events"} failed: ${response.status}`);
  }
  const payload = (await response.json()) as unknown;
  return Array.isArray(payload) ? (payload as GammaEvent[]) : [];
}

/** Gamma caps responses at 100 rows — paginate until exhausted. */
async function fetchGammaEventsPaginated(
  params: Record<string, string>,
): Promise<GammaEvent[]> {
  const rows: GammaEvent[] = [];
  for (let offset = 0; offset < 2000; offset += GAMMA_PAGE_SIZE) {
    const page = await fetchGammaEventsPage({
      ...params,
      closed: "false",
      limit: String(GAMMA_PAGE_SIZE),
      offset: String(offset),
    });
    rows.push(...page);
    if (page.length < GAMMA_PAGE_SIZE) break;
  }
  return rows;
}

async function fetchGammaEventsByTag(tag: string): Promise<GammaEvent[]> {
  return fetchGammaEventsPaginated({ tag_slug: tag });
}

/** Full World Cup fixture surface — sibling prop events share this series. */
async function fetchFifwcSeriesEvents(): Promise<GammaEvent[]> {
  return fetchGammaEventsPaginated({ series_slug: "soccer-fifwc" });
}

function dedupeEvents(events: CatalogEvent[]): CatalogEvent[] {
  const bySlug = new Map<string, CatalogEvent>();
  for (const event of events) {
    const existing = bySlug.get(event.slug);
    if (!existing || event.marketCount > existing.marketCount) {
      bySlug.set(event.slug, event);
    }
  }
  return [...bySlug.values()].sort((a, b) => {
    const ak = a.kickoffUtc ? new Date(a.kickoffUtc).getTime() : Number.MAX_SAFE_INTEGER;
    const bk = b.kickoffUtc ? new Date(b.kickoffUtc).getTime() : Number.MAX_SAFE_INTEGER;
    if (ak !== bk) return ak - bk;
    return a.title.localeCompare(b.title);
  });
}

function buildStats(
  events: CatalogEvent[],
  matches: CatalogMatch[],
): VenueCatalog["stats"] {
  const categories: Record<string, number> = {};
  let markets = 0;
  let openEvents = 0;
  for (const event of events) {
    categories[event.category] = (categories[event.category] ?? 0) + 1;
    markets += event.marketCount;
    if (!event.closed) openEvents += 1;
  }
  return {
    events: events.length,
    markets,
    openEvents,
    categories,
    matches: matches.length,
  };
}

const MATCH_SUBEVENT_ORDER = [
  "Match result",
  "More Markets",
  "Exact Score",
  "Halftime Result",
  "Second Half Result",
  "First To Score",
  "First Team To Score",
];

function subEventSortKey(label: string): number {
  const idx = MATCH_SUBEVENT_ORDER.findIndex(
    (entry) => entry.toLowerCase() === label.toLowerCase(),
  );
  return idx >= 0 ? idx : MATCH_SUBEVENT_ORDER.length + label.charCodeAt(0);
}

/** Collapse fifwc-* sibling events into one browsable match row. */
export function groupMatchEvents(events: CatalogEvent[]): CatalogMatch[] {
  const buckets = new Map<string, CatalogEvent[]>();

  for (const event of events) {
    const base = event.matchBaseSlug;
    if (!base) continue;
    const list = buckets.get(base) ?? [];
    list.push(event);
    buckets.set(base, list);
  }

  const matches: CatalogMatch[] = [];
  for (const [baseSlug, subEvents] of buckets) {
    subEvents.sort(
      (a, b) =>
        subEventSortKey(a.subEventLabel) - subEventSortKey(b.subEventLabel) ||
        a.slug.localeCompare(b.slug),
    );

    const main =
      subEvents.find((e) => e.slug === baseSlug) ??
      subEvents.find((e) => e.subEventLabel === "Match result") ??
      subEvents[0];
    const teams = parseTeamsFromTitle(main.title);
    const liveState =
      subEvents.find((e) => e.liveState?.live)?.liveState ??
      subEvents.find((e) => e.liveState)?.liveState ??
      null;

    const statusPriority = (status: CatalogStatus) =>
      status === "live" ? 0 : status === "upcoming" ? 1 : 2;
    const status = subEvents.reduce<CatalogStatus>(
      (best, event) =>
        statusPriority(event.status) < statusPriority(best) ? event.status : best,
      "finished",
    );

    matches.push({
      baseSlug,
      title: teams ? `${teams[0]} vs. ${teams[1]}` : main.title,
      home: teams?.[0] ?? "",
      away: teams?.[1] ?? "",
      category: main.category,
      status,
      kickoffUtc: main.kickoffUtc,
      liquidity: subEvents.reduce((sum, e) => sum + (e.liquidity ?? 0), 0) || null,
      volume24h: subEvents.reduce((sum, e) => sum + (e.volume24h ?? 0), 0) || null,
      closed: subEvents.every((e) => e.closed),
      marketCount: subEvents.reduce((sum, e) => sum + e.marketCount, 0),
      subEventCount: subEvents.length,
      subEvents,
      liveState,
      polymarketUrl: main.polymarketUrl,
      byrealUrl: main.byrealUrl,
    });
  }

  return matches.sort((a, b) => {
    const ak = a.kickoffUtc ? new Date(a.kickoffUtc).getTime() : Number.MAX_SAFE_INTEGER;
    const bk = b.kickoffUtc ? new Date(b.kickoffUtc).getTime() : Number.MAX_SAFE_INTEGER;
    if (ak !== bk) return ak - bk;
    return a.title.localeCompare(b.title);
  });
}

function wrapVenueCatalog(
  venue: VenueCatalog["venue"],
  label: string,
  tagline: string,
  accent: VenueCatalog["accent"],
  events: CatalogEvent[],
  fetchedAt: string,
): VenueCatalog {
  const matches = groupMatchEvents(events);
  return {
    venue,
    label,
    tagline,
    accent,
    fetchedAt,
    stats: buildStats(events, matches),
    events,
    matches,
  };
}

export async function fetchMarketsCatalog(): Promise<MarketsCatalogResponse> {
  const fetchedAt = new Date().toISOString();

  const [tagResults, fifwcSeriesRows] = await Promise.all([
    Promise.all(
      POLYMARKET_SPORTS_TAGS.map(async (tag) => {
        const rows = await fetchGammaEventsByTag(tag);
        return rows
          .map((row) => parseGammaEvent(row, tag))
          .filter((event): event is CatalogEvent => event != null);
      }),
    ),
    fetchFifwcSeriesEvents().then((rows) =>
      rows
        .map((row) => parseGammaEvent(row, "fifa-world-cup"))
        .filter((event): event is CatalogEvent => event != null),
    ),
  ]);

  const polymarketEvents = dedupeEvents([...tagResults.flat(), ...fifwcSeriesRows]);
  const byrealEvents = polymarketEvents
    .filter((e) => isByrealCurated(e.slug, e.title))
    .map((e) => ({
      ...e,
      category: byrealCategory(e.slug, e.title),
      byrealUrl: byrealUrlForEvent(e.slug),
    }));

  return {
    fetchedAt,
    polymarket: wrapVenueCatalog(
      "polymarket",
      "Polymarket",
      "Full sports catalog from Gamma — all open events across major tags.",
      "emerald",
      polymarketEvents,
      fetchedAt,
    ),
    byreal: wrapVenueCatalog(
      "byreal",
      "Byreal Predict",
      "Bybit-incubated front-end. Same Polymarket CLOB liquidity, curated for World Cup · NBA · MLB.",
      "amber",
      byrealEvents,
      fetchedAt,
    ),
  };
}
