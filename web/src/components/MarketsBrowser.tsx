"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { formatKickoff } from "@/core/fixtures";
import type {
  CatalogEvent,
  CatalogMatch,
  CatalogMarket,
  MarketsCatalogResponse,
  PolyLiveState,
  VenueCatalog,
} from "@/core/marketCatalog";
import {
  formatSportUpdateLine,
  type PolySportUpdate,
} from "@/core/polySportsFeed";

type VenueKey = "polymarket" | "byreal";
type LayoutMode = "split" | VenueKey;
type BrowseMode = "matches" | "events";

const CATEGORY_LABELS: Record<string, string> = {
  "fifa-world-cup": "World Cup",
  mlb: "MLB",
  nba: "NBA",
  nfl: "NFL",
  soccer: "Soccer",
  ucl: "UCL",
  tennis: "Tennis",
  golf: "Golf",
  football: "Football",
  basketball: "Basketball",
  baseball: "Baseball",
  other: "Other",
};

const MAX_LOG_LINES = 120;

function formatUsd(n: number | null): string {
  if (n == null || !Number.isFinite(n)) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function statusClass(status: CatalogEvent["status"]): string {
  if (status === "live") return "bg-red-500/15 text-red-300 border-red-500/30";
  if (status === "upcoming") return "bg-cyan-500/10 text-cyan-200 border-cyan-500/25";
  return "bg-zinc-500/10 text-zinc-400 border-zinc-500/25";
}

function LiveScoreBanner({ live }: { live: PolyLiveState }) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-3 rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm">
      <span className="inline-flex items-center gap-1.5 font-semibold text-red-200">
        <span className="h-2 w-2 animate-pulse rounded-full bg-red-400" />
        {live.live ? "LIVE" : live.ended ? "FT" : "Match"}
      </span>
      <span className="font-mono text-lg text-white">{live.score || "—"}</span>
      <span className="text-[var(--muted)]">
        {[live.period, live.elapsed ? `${live.elapsed}'` : ""].filter(Boolean).join(" · ")}
      </span>
      <span className="text-[var(--muted)]">
        {live.homeTeam || live.homeAbbrev} vs {live.awayTeam || live.awayAbbrev}
      </span>
    </div>
  );
}

export function MarketsBrowser() {
  const [catalog, setCatalog] = useState<MarketsCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layout, setLayout] = useState<LayoutMode>("polymarket");
  const [browseMode, setBrowseMode] = useState<BrowseMode>("matches");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("fifa-world-cup");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [liveLog, setLiveLog] = useState<string[]>([]);
  const [streamStatus, setStreamStatus] = useState<"off" | "connecting" | "live" | "error">(
    "off",
  );
  const logRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/markets/catalog", { cache: "no-store" });
      const payload = (await response.json()) as MarketsCatalogResponse & { error?: string };
      if (!response.ok) throw new Error(payload.error ?? "Catalog fetch failed");
      setCatalog(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Catalog fetch failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setStreamStatus("connecting");
    const source = new EventSource("/api/sports/stream?league=fifwc");

    const pushLog = (line: string) => {
      setLiveLog((prev) => [...prev.slice(-(MAX_LOG_LINES - 1)), line]);
    };

    source.addEventListener("connected", () => setStreamStatus("live"));
    source.addEventListener("ready", () => pushLog("Sports feed connected (fifwc filter)"));
    source.addEventListener("sport", (event) => {
      try {
        const update = JSON.parse((event as MessageEvent).data) as PolySportUpdate;
        pushLog(formatSportUpdateLine(update));
      } catch {
        /* ignore malformed */
      }
    });
    source.addEventListener("error", () => {
      setStreamStatus("error");
      pushLog("Sports feed error — reconnect by refreshing the page");
    });
    source.addEventListener("closed", () => setStreamStatus("off"));

    return () => source.close();
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [liveLog]);

  const polyCategories = useMemo(
    () => Object.keys(catalog?.polymarket.stats.categories ?? {}).sort(),
    [catalog],
  );
  const byrealCategories = useMemo(
    () => Object.keys(catalog?.byreal.stats.categories ?? {}).sort(),
    [catalog],
  );

  return (
    <div className="mx-auto min-h-screen max-w-[1600px] px-4 py-8 sm:px-6 sm:py-10">
      <header className="mb-8">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Link
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--muted)] transition hover:border-emerald-500/30 hover:text-emerald-200"
            href="/"
          >
            ← Analyzer
          </Link>
          <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            All-in-one venue hub
          </span>
        </div>
        <h1 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
          Polymarket · Bybit (Byreal)
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--muted)] sm:text-base">
          Browse World Cup matches and every sub-market Polymarket lists — moneyline,
          totals, spreads, exact score, halves, and combo-eligible lines when they
          appear. Same CLOB liquidity on Byreal Predict (Bybit-incubated). Fund
          transfers between venues later; for now this is read-only discovery +
          live score feed.
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex rounded-xl border border-[var(--border)] p-1">
          {(
            [
              ["split", "Split"],
              ["polymarket", "Polymarket"],
              ["byreal", "Bybit / Byreal"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                layout === key
                  ? "bg-white/10 text-white"
                  : "text-[var(--muted)] hover:text-white"
              }`}
              type="button"
              onClick={() => setLayout(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex rounded-xl border border-[var(--border)] p-1">
          {(
            [
              ["matches", "World Cup matches"],
              ["events", "All events"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                browseMode === key
                  ? "bg-emerald-500/15 text-emerald-200"
                  : "text-[var(--muted)] hover:text-white"
              }`}
              type="button"
              onClick={() => setBrowseMode(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <input
          className="min-w-[220px] flex-1 rounded-xl border border-[var(--border)] bg-black/20 px-3.5 py-2 text-sm outline-none ring-emerald-500/30 placeholder:text-[var(--muted)] focus:ring-2"
          placeholder="Search teams, slugs, market questions…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <button
          className="rounded-xl border border-[var(--border)] px-3.5 py-2 text-sm font-medium text-[var(--muted)] transition hover:border-emerald-500/30 hover:text-emerald-200 disabled:opacity-50"
          disabled={loading}
          type="button"
          onClick={() => void load()}
        >
          {loading ? "Refreshing…" : "Refresh catalog"}
        </button>
      </div>

      {error ? (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      <div
        className={`grid gap-6 ${
          layout === "split" ? "xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" : "grid-cols-1"
        }`}
      >
        {loading && !catalog ? (
          <CatalogSkeleton layout={layout} />
        ) : catalog ? (
          <>
            {(layout === "split" || layout === "polymarket") && (
              <VenueColumn
                browseMode={browseMode}
                categories={polyCategories}
                category={category}
                expanded={expanded}
                layout={layout}
                query={query}
                venue={catalog.polymarket}
                onCategoryChange={setCategory}
                onToggle={(key) =>
                  setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
                }
              />
            )}
            {(layout === "split" || layout === "byreal") && (
              <VenueColumn
                browseMode={browseMode}
                categories={byrealCategories}
                category={category}
                expanded={expanded}
                layout={layout}
                query={query}
                venue={catalog.byreal}
                onCategoryChange={setCategory}
                onToggle={(key) =>
                  setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
                }
              />
            )}
          </>
        ) : null}
      </div>

      <LiveSportsLog log={liveLog} status={streamStatus} logRef={logRef} />

      {catalog ? (
        <p className="mt-8 text-center text-xs text-[var(--muted)]">
          Catalog fetched {new Date(catalog.fetchedAt).toLocaleString()} · Gamma REST +
          Polymarket sports WebSocket · DRY_RUN — browse only, no orders
        </p>
      ) : null}
    </div>
  );
}

function LiveSportsLog({
  log,
  status,
  logRef,
}: {
  log: string[];
  status: "off" | "connecting" | "live" | "error";
  logRef: React.RefObject<HTMLDivElement | null>;
}) {
  const statusLabel =
    status === "live"
      ? "Streaming"
      : status === "connecting"
        ? "Connecting…"
        : status === "error"
          ? "Error"
          : "Offline";

  return (
    <section className="glass mt-8 overflow-hidden rounded-2xl border border-cyan-500/20">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-cyan-200">
            Live sports log · Polymarket feed
          </h2>
          <p className="text-xs text-[var(--muted)]">
            Same scoreboard stream that powers the ball widget on polymarket.com — fifwc
            filter only
          </p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
            status === "live"
              ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
              : "border-[var(--border)] text-[var(--muted)]"
          }`}
        >
          {statusLabel}
        </span>
      </div>
      <div
        ref={logRef}
        className="max-h-56 overflow-y-auto bg-black/30 px-4 py-3 font-mono text-xs leading-relaxed text-cyan-100/90"
      >
        {log.length === 0 ? (
          <p className="text-[var(--muted)]">Waiting for World Cup score updates…</p>
        ) : (
          log.map((line, i) => (
            <div key={`${i}-${line.slice(0, 24)}`} className="whitespace-pre-wrap">
              {line}
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function VenueColumn({
  venue,
  categories,
  category,
  query,
  expanded,
  layout,
  browseMode,
  onCategoryChange,
  onToggle,
}: {
  venue: VenueCatalog;
  categories: string[];
  category: string;
  query: string;
  expanded: Record<string, boolean>;
  layout: LayoutMode;
  browseMode: BrowseMode;
  onCategoryChange: (value: string) => void;
  onToggle: (key: string) => void;
}) {
  const accent =
    venue.accent === "emerald"
      ? {
          border: "border-emerald-500/25",
          glow: "shadow-[0_0_40px_-12px_rgba(52,211,153,0.35)]",
          pill: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
          link: "text-emerald-300 hover:text-emerald-200",
          bar: "bg-emerald-400",
        }
      : {
          border: "border-amber-500/25",
          glow: "shadow-[0_0_40px_-12px_rgba(251,191,36,0.3)]",
          pill: "bg-amber-500/15 text-amber-200 border-amber-500/30",
          link: "text-amber-300 hover:text-amber-200",
          bar: "bg-amber-400",
        };

  const filteredMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return venue.matches.filter((match) => {
      if (category !== "all" && match.category !== category) return false;
      if (!q) return true;
      if (match.title.toLowerCase().includes(q)) return true;
      if (match.baseSlug.toLowerCase().includes(q)) return true;
      return match.subEvents.some((sub) =>
        sub.markets.some(
          (m) =>
            m.question.toLowerCase().includes(q) ||
            m.groupTitle.toLowerCase().includes(q),
        ),
      );
    });
  }, [venue.matches, category, query]);

  const filteredEvents = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matchSlugs = new Set(
      venue.matches.flatMap((m) => m.subEvents.map((e) => e.slug)),
    );
    return venue.events.filter((event) => {
      if (matchSlugs.has(event.slug)) return false;
      if (category !== "all" && event.category !== category) return false;
      if (!q) return true;
      if (event.title.toLowerCase().includes(q)) return true;
      if (event.slug.toLowerCase().includes(q)) return true;
      return event.markets.some(
        (m) =>
          m.question.toLowerCase().includes(q) ||
          m.groupTitle.toLowerCase().includes(q),
      );
    });
  }, [venue.events, venue.matches, category, query]);

  const showMatches = browseMode === "matches" && filteredMatches.length > 0;
  const listCount = showMatches ? filteredMatches.length : filteredEvents.length;

  return (
    <section
      className={`glass overflow-hidden rounded-2xl ${accent.border} ${accent.glow}`}
    >
      <div className="sticky top-0 z-10 border-b border-[var(--border)] bg-[rgba(10,14,18,0.92)] px-4 py-4 backdrop-blur-md sm:px-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${accent.bar}`} />
              <h2 className="text-lg font-semibold">{venue.label}</h2>
            </div>
            <p className="text-xs leading-relaxed text-[var(--muted)] sm:text-sm">
              {venue.tagline}
            </p>
          </div>
          {layout === "split" ? (
            <div className="text-right text-xs text-[var(--muted)]">
              <div className="font-mono text-sm text-white">
                {listCount}
                <span className="text-[var(--muted)]">
                  {" "}
                  / {showMatches ? venue.stats.matches : venue.stats.events}
                </span>
              </div>
              <div>{venue.stats.markets} markets total</div>
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <CategoryChip
            active={category === "all"}
            label={`All (${venue.stats.events})`}
            onClick={() => onCategoryChange("all")}
          />
          {categories.map((cat) => (
            <CategoryChip
              key={cat}
              active={category === cat}
              label={`${CATEGORY_LABELS[cat] ?? cat} (${venue.stats.categories[cat] ?? 0})`}
              onClick={() => onCategoryChange(cat)}
            />
          ))}
        </div>
      </div>

      <div className="max-h-[calc(100vh-14rem)] overflow-y-auto px-2 py-2 sm:px-3">
        {showMatches ? (
          filteredMatches.length === 0 ? (
            <EmptyState />
          ) : (
            <ul className="space-y-2">
              {filteredMatches.map((match) => (
                <MatchCard
                  key={`${venue.venue}-${match.baseSlug}`}
                  accentLink={accent.link}
                  accentPill={accent.pill}
                  expanded={Boolean(expanded[match.baseSlug])}
                  match={match}
                  venue={venue.venue}
                  onToggle={() => onToggle(match.baseSlug)}
                />
              ))}
            </ul>
          )
        ) : filteredEvents.length === 0 && filteredMatches.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="space-y-2">
            {filteredEvents.map((event) => (
              <EventCard
                key={`${venue.venue}-${event.slug}`}
                accentLink={accent.link}
                accentPill={accent.pill}
                event={event}
                expanded={Boolean(expanded[event.slug])}
                venue={venue.venue}
                onToggle={() => onToggle(event.slug)}
              />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function EmptyState() {
  return (
    <div className="px-3 py-12 text-center text-sm text-[var(--muted)]">
      No events match your filters.
    </div>
  );
}

function CategoryChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${
        active
          ? "border-white/20 bg-white/10 text-white"
          : "border-[var(--border)] text-[var(--muted)] hover:text-white"
      }`}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function MatchCard({
  match,
  venue,
  expanded,
  accentPill,
  accentLink,
  onToggle,
}: {
  match: CatalogMatch;
  venue: VenueKey;
  expanded: boolean;
  accentPill: string;
  accentLink: string;
  onToggle: () => void;
}) {
  const analyzeHref = `/?fixture=${encodeURIComponent(match.baseSlug)}`;

  return (
    <li className="rounded-xl border border-[var(--border)]/80 bg-black/15">
      <button
        className="flex w-full items-start gap-3 px-3 py-3 text-left sm:px-4"
        type="button"
        onClick={onToggle}
      >
        <span
          className={`mt-1 shrink-0 text-[var(--muted)] transition ${expanded ? "rotate-90" : ""}`}
        >
          ▸
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClass(match.status)}`}
            >
              {match.status}
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${accentPill}`}
            >
              {CATEGORY_LABELS[match.category] ?? match.category}
            </span>
            <span className="text-[10px] text-[var(--muted)]">
              {match.marketCount} mkts · {match.subEventCount} sheets
            </span>
          </div>
          <h3 className="text-sm font-semibold leading-snug sm:text-base">{match.title}</h3>
          {match.liveState ? (
            <div className="mt-1 font-mono text-sm text-red-200">
              {match.liveState.score}{" "}
              <span className="text-xs text-[var(--muted)]">
                {[match.liveState.period, match.liveState.elapsed ? `${match.liveState.elapsed}'` : ""]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>
          ) : null}
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--muted)]">
            {match.kickoffUtc ? <span>{formatKickoff(match.kickoffUtc)}</span> : null}
            <span>Liq {formatUsd(match.liquidity)}</span>
            <span>24h {formatUsd(match.volume24h)}</span>
          </div>
        </div>
      </button>

      {expanded ? (
        <div className="border-t border-[var(--border)]/70 px-3 pb-3 sm:px-4">
          {match.liveState ? <LiveScoreBanner live={match.liveState} /> : null}
          <div className="mb-4 flex flex-wrap gap-2 pt-1">
            <a
              className={`text-xs font-medium underline-offset-2 hover:underline ${accentLink}`}
              href={match.polymarketUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              Open on Polymarket ↗
            </a>
            {venue === "byreal" && match.byrealUrl ? (
              <a
                className="text-xs font-medium text-amber-300 underline-offset-2 hover:text-amber-200 hover:underline"
                href={match.byrealUrl}
                rel="noopener noreferrer"
                target="_blank"
              >
                Open on Byreal (Bybit) ↗
              </a>
            ) : null}
            <Link
              className="text-xs font-medium text-cyan-300 underline-offset-2 hover:text-cyan-200 hover:underline"
              href={analyzeHref}
            >
              Analyze in fv-match →
            </Link>
          </div>

          <div className="space-y-4">
            {match.subEvents.map((sub) => (
              <SubEventMarkets
                key={sub.slug}
                accentLink={accentLink}
                subEvent={sub}
              />
            ))}
          </div>
        </div>
      ) : null}
    </li>
  );
}

function SubEventMarkets({
  subEvent,
  accentLink,
}: {
  subEvent: CatalogEvent;
  accentLink: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)]/60 bg-black/10">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)]/50 px-3 py-2">
        <div>
          <h4 className="text-sm font-semibold">{subEvent.subEventLabel}</h4>
          <p className="text-[11px] text-[var(--muted)]">
            {subEvent.marketCount} markets · {subEvent.slug}
          </p>
        </div>
        <a
          className={`text-[11px] font-medium underline-offset-2 hover:underline ${accentLink}`}
          href={subEvent.polymarketUrl}
          rel="noopener noreferrer"
          target="_blank"
        >
          Event ↗
        </a>
      </div>
      <MarketsTable markets={subEvent.markets} />
    </div>
  );
}

function EventCard({
  event,
  venue,
  expanded,
  accentPill,
  accentLink,
  onToggle,
}: {
  event: CatalogEvent;
  venue: VenueKey;
  expanded: boolean;
  accentPill: string;
  accentLink: string;
  onToggle: () => void;
}) {
  const analyzeHref =
    event.slug.startsWith("fifwc-") && event.subEventLabel === "Match result"
      ? `/?fixture=${encodeURIComponent(event.slug)}`
      : null;

  return (
    <li className="rounded-xl border border-[var(--border)]/80 bg-black/15">
      <button
        className="flex w-full items-start gap-3 px-3 py-3 text-left sm:px-4"
        type="button"
        onClick={onToggle}
      >
        <span
          className={`mt-1 shrink-0 text-[var(--muted)] transition ${expanded ? "rotate-90" : ""}`}
        >
          ▸
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClass(event.status)}`}
            >
              {event.status}
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${accentPill}`}
            >
              {CATEGORY_LABELS[event.category] ?? event.category}
            </span>
            <span className="text-[10px] text-[var(--muted)]">{event.marketCount} mkts</span>
          </div>
          <h3 className="text-sm font-semibold leading-snug sm:text-base">{event.title}</h3>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--muted)]">
            {event.kickoffUtc ? <span>{formatKickoff(event.kickoffUtc)}</span> : null}
            <span>Liq {formatUsd(event.liquidity)}</span>
            <span>24h {formatUsd(event.volume24h)}</span>
          </div>
        </div>
      </button>

      {expanded ? (
        <div className="border-t border-[var(--border)]/70 px-3 pb-3 sm:px-4">
          {event.liveState ? <LiveScoreBanner live={event.liveState} /> : null}
          <div className="mb-3 flex flex-wrap gap-2 pt-3">
            <a
              className={`text-xs font-medium underline-offset-2 hover:underline ${accentLink}`}
              href={event.polymarketUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              Open on Polymarket ↗
            </a>
            {venue === "byreal" && event.byrealUrl ? (
              <a
                className="text-xs font-medium text-amber-300 underline-offset-2 hover:text-amber-200 hover:underline"
                href={event.byrealUrl}
                rel="noopener noreferrer"
                target="_blank"
              >
                Open on Byreal (Bybit) ↗
              </a>
            ) : null}
            {analyzeHref ? (
              <Link
                className="text-xs font-medium text-cyan-300 underline-offset-2 hover:text-cyan-200 hover:underline"
                href={analyzeHref}
              >
                Analyze in fv-match →
              </Link>
            ) : null}
          </div>
          <MarketsTable markets={event.markets} />
        </div>
      ) : null}
    </li>
  );
}

function MarketsTable({ markets }: { markets: CatalogMarket[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[10px] uppercase tracking-wide text-[var(--muted)]">
            <th className="px-3 py-2">Market</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2 text-right">Yes</th>
            <th className="px-3 py-2 text-right">No</th>
            <th className="px-3 py-2 text-right">Liq</th>
          </tr>
        </thead>
        <tbody>
          {markets.map((market) => (
            <tr
              key={market.id}
              className="border-b border-[var(--border)]/50 last:border-0"
            >
              <td className="px-3 py-2">
                <div className="font-medium leading-snug">
                  {market.groupTitle || market.question}
                </div>
                {market.groupTitle && market.question ? (
                  <div className="mt-0.5 text-[11px] text-[var(--muted)]">
                    {market.question}
                  </div>
                ) : null}
                {market.comboStatus && market.comboStatus !== "disabled" ? (
                  <span className="mt-1 inline-block rounded border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 text-[10px] text-violet-200">
                    combo · {market.comboStatus}
                  </span>
                ) : null}
              </td>
              <td className="px-3 py-2 text-[11px] text-[var(--muted)]">
                {market.sportsMarketType || "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {market.yesPrice != null ? (
                  <>
                    {(market.yesPrice * 100).toFixed(1)}¢
                    {market.yesOdds ? (
                      <span className="ml-1 text-[var(--muted)]">
                        ({market.yesOdds.toFixed(2)})
                      </span>
                    ) : null}
                  </>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {market.noPrice != null ? (
                  <>
                    {(market.noPrice * 100).toFixed(1)}¢
                    {market.noOdds ? (
                      <span className="ml-1 text-[var(--muted)]">
                        ({market.noOdds.toFixed(2)})
                      </span>
                    ) : null}
                  </>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-3 py-2 text-right font-mono text-[var(--muted)]">
                {formatUsd(market.liquidity)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CatalogSkeleton({ layout }: { layout: LayoutMode }) {
  const cols = layout === "split" ? 2 : 1;
  return (
    <>
      {Array.from({ length: cols }).map((_, i) => (
        <div
          key={i}
          className="glass h-[70vh] animate-pulse rounded-2xl border border-[var(--border)]"
        />
      ))}
    </>
  );
}
