"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import type { CatalogMarket } from "@/core/marketCatalog";
import type { MatchSurface, MatchTab } from "@/core/gameSurface";

const TABS: { id: MatchTab; label: string }[] = [
  { id: "game-lines", label: "Game Lines" },
  { id: "exact-score", label: "Exact Score" },
  { id: "halves", label: "Halves" },
  { id: "corners", label: "Corners" },
  { id: "goals", label: "Goals" },
  { id: "assists", label: "Assists" },
  { id: "shots", label: "Shots" },
];

function formatPrice(price: number | null): string {
  if (price == null) return "—";
  return `${(price * 100).toFixed(1)}¢`;
}

function formatPct(price: number | null): string {
  if (price == null) return "—";
  return `${(price * 100).toFixed(1)}%`;
}

export function MatchDetail({ baseSlug }: { baseSlug: string }) {
  const [surface, setSurface] = useState<MatchSurface | null>(null);
  const [tab, setTab] = useState<MatchTab>("game-lines");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(
        `/api/markets/match/${encodeURIComponent(baseSlug)}`,
        { cache: "no-store" },
      );
      const payload = (await response.json()) as MatchSurface & { error?: string };
      if (!response.ok) throw new Error(payload.error ?? "Failed to load match");
      setSurface(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load match");
    } finally {
      setLoading(false);
    }
  }, [baseSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!surface?.liveState?.live) return;
    const timer = setInterval(() => void load(), 15_000);
    return () => clearInterval(timer);
  }, [surface?.liveState?.live, load]);

  if (loading && !surface) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-16 text-center text-sm text-[var(--muted)]">
        Loading full market surface…
      </main>
    );
  }

  if (error || !surface) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-16">
        <p className="mb-4 text-sm text-red-300">{error ?? "Match not found"}</p>
        <Link className="text-sm text-cyan-300 hover:underline" href="/markets">
          ← Back to markets
        </Link>
      </main>
    );
  }

  const live = surface.liveState;
  const ml = surface.moneyline;
  const tabMarkets = surface.tabs[tab] ?? [];
  const polyUrl = `https://polymarket.com/event/${surface.baseSlug}`;

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Link
          className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--muted)] hover:text-white"
          href="/markets"
        >
          ← Markets
        </Link>
        <span className="text-xs text-[var(--muted)]">
          {surface.marketCount} markets · {surface.subEvents.length} event sheets · refreshed{" "}
          {new Date(surface.fetchedAt).toLocaleTimeString()}
        </span>
      </div>

      {/* Live scoreboard — same Gamma fields as Polymarket widget */}
      <section className="glass mb-6 overflow-hidden rounded-2xl border border-emerald-500/20">
        <div className="border-b border-[var(--border)] px-4 py-3 sm:px-6">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            World Cup · {live?.live ? "Live" : live?.ended ? "Final" : "Match"}
          </div>
          <h1 className="text-2xl font-bold sm:text-3xl">{surface.title}</h1>
        </div>

        <div className="grid gap-4 px-4 py-5 sm:grid-cols-[1fr_auto_1fr] sm:items-center sm:px-6">
          <TeamBlock abbrev={live?.homeAbbrev} name={surface.home} align="left" />
          <div className="text-center">
            {live ? (
              <>
                <div className="font-mono text-4xl font-bold tracking-tight sm:text-5xl">
                  {live.score || "0-0"}
                </div>
                <div className="mt-1 text-sm text-red-300">
                  {live.live ? (
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-red-400" />
                      {live.period}
                      {live.elapsed ? ` · ${live.elapsed}'` : ""}
                    </span>
                  ) : (
                    live.period || "Scheduled"
                  )}
                </div>
              </>
            ) : (
              <div className="text-sm text-[var(--muted)]">Kickoff pending</div>
            )}
          </div>
          <TeamBlock abbrev={live?.awayAbbrev} name={surface.away} align="right" />
        </div>

        {/* Moneyline bar like Polymarket */}
        <div className="border-t border-[var(--border)] bg-black/20 px-4 py-4 sm:px-6">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Match result (Reg Time)
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-sm">
            <MoneylineCell label="Draw" pct={ml.drawPct} price={ml.draw?.yesPrice ?? null} />
            <MoneylineCell label={surface.home} pct={ml.homePct} price={ml.home?.yesPrice ?? null} />
            <MoneylineCell label={surface.away} pct={ml.awayPct} price={ml.away?.yesPrice ?? null} />
          </div>
        </div>
      </section>

      {/* Combos note */}
      <section className="mb-6 rounded-xl border border-violet-500/20 bg-violet-500/5 px-4 py-3 text-sm text-violet-100/90">
        <span className="font-semibold text-violet-200">Combos</span> — Polymarket builds
        3-pick parlays in their UI from combo-eligible lines below. We surface every leg +
        combo status here; placing combos (and all orders) stays{" "}
        <span className="font-semibold">DRY_RUN</span> until execution is wired.
      </section>

      {/* Tabs */}
      <div className="mb-4 flex flex-wrap gap-2 border-b border-[var(--border)] pb-3">
        {TABS.map(({ id, label }) => {
          const count = surface.tabs[id]?.length ?? 0;
          return (
            <button
              key={id}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                tab === id
                  ? "bg-emerald-500/15 text-emerald-200"
                  : "text-[var(--muted)] hover:text-white"
              }`}
              type="button"
              onClick={() => setTab(id)}
            >
              {label}
              <span className="ml-1 text-xs opacity-70">({count})</span>
            </button>
          );
        })}
      </div>

      <div className="mb-4 flex flex-wrap gap-3">
        <a
          className="rounded-xl bg-emerald-500/90 px-4 py-2 text-sm font-semibold text-emerald-950 hover:bg-emerald-400"
          href={polyUrl}
          rel="noopener noreferrer"
          target="_blank"
        >
          Trade on Polymarket ↗
        </a>
        <button
          className="rounded-xl border border-[var(--border)] px-4 py-2 text-sm text-[var(--muted)] hover:text-white"
          type="button"
          onClick={() => void load()}
        >
          Refresh prices
        </button>
      </div>

      {tabMarkets.length === 0 ? (
        <p className="py-12 text-center text-sm text-[var(--muted)]">
          No markets in this tab for this match.
        </p>
      ) : (
        <div className="space-y-2">
          {tabMarkets.map((market) => (
            <MarketRow key={market.id} market={market} />
          ))}
        </div>
      )}

      <p className="mt-8 text-center text-xs text-[var(--muted)]">
        Read-only discovery · Gamma API · Yes/No buttons are disabled (DRY_RUN). Use Polymarket
        to place orders.
      </p>
    </main>
  );
}

function TeamBlock({
  name,
  abbrev,
  align,
}: {
  name: string;
  abbrev?: string;
  align: "left" | "right";
}) {
  return (
    <div className={align === "right" ? "text-right" : "text-left"}>
      <div className="text-lg font-semibold sm:text-xl">{name}</div>
      {abbrev ? <div className="text-xs uppercase text-[var(--muted)]">{abbrev}</div> : null}
    </div>
  );
}

function MoneylineCell({
  label,
  pct,
  price,
}: {
  label: string;
  pct: number | null;
  price: number | null;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)]/60 bg-black/15 px-2 py-2">
      <div className="truncate text-xs text-[var(--muted)]">{label}</div>
      <div className="font-mono text-lg font-semibold">{formatPct(price)}</div>
      <div className="text-[11px] text-[var(--muted)]">{formatPrice(price)}</div>
    </div>
  );
}

function MarketRow({ market }: { market: CatalogMarket }) {
  const title = market.groupTitle || market.question;
  const comboEligible =
    market.comboStatus && market.comboStatus !== "disabled";

  return (
    <div className="glass rounded-xl border border-[var(--border)]/70 px-4 py-3 sm:px-5">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="font-medium leading-snug">{title}</div>
          {market.groupTitle && market.question ? (
            <div className="mt-0.5 text-xs text-[var(--muted)]">{market.question}</div>
          ) : null}
          <div className="mt-1 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-[var(--muted)]">
            {market.sportsMarketType ? <span>{market.sportsMarketType}</span> : null}
            {comboEligible ? (
              <span className="rounded border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 text-violet-200">
                combo · {market.comboStatus}
              </span>
            ) : null}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <OutcomeButton label="Yes" odds={market.yesOdds} price={market.yesPrice} tone="yes" />
        <OutcomeButton label="No" odds={market.noOdds} price={market.noPrice} tone="no" />
      </div>
    </div>
  );
}

function OutcomeButton({
  label,
  price,
  odds,
  tone,
}: {
  label: string;
  price: number | null;
  odds: number | null;
  tone: "yes" | "no";
}) {
  const colors =
    tone === "yes"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
      : "border-zinc-500/30 bg-zinc-500/10 text-zinc-200";

  return (
    <button
      className={`min-w-[120px] flex-1 rounded-xl border px-3 py-2 text-left opacity-60 cursor-not-allowed ${colors}`}
      disabled
      title="DRY_RUN — view only. Trade on Polymarket to place orders."
      type="button"
    >
      <div className="text-[10px] font-semibold uppercase tracking-wide opacity-80">
        {label} · dry-run
      </div>
      <div className="font-mono text-lg font-semibold">{formatPrice(price)}</div>
      {odds ? (
        <div className="text-[11px] opacity-70">{odds.toFixed(2)} decimal</div>
      ) : null}
    </button>
  );
}
