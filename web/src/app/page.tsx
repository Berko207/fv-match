"use client";

import { useCallback, useEffect, useState } from "react";

import { AnalysisResults } from "@/components/AnalysisResults";
import { EdgeArbTables } from "@/components/EdgeArbTables";
import { MatchForm, type MatchFormValues } from "@/components/MatchForm";
import { detectLocks, edgeSweep } from "@/core/arb";
import {
  fixtureToFormValues,
  pickDefaultFixture,
  type FwcFixture,
} from "@/core/fixtures";
import type { MatchAnalysis } from "@/core/engine";
import { analyzeMatch } from "@/core/engine";
import type { LiveState } from "@/core/live";
import type { SiblingMarkets } from "@/core/markets";

const FALLBACK_FORM: MatchFormValues = {
  home: "Portugal",
  away: "Uzbekistan",
  homeOdds: "",
  drawOdds: "",
  awayOdds: "",
  neutral: true,
  inPlay: false,
  minute: "0",
  homeGoals: "0",
  awayGoals: "0",
  redHome: "0",
  redAway: "0",
};

function parseOdds(raw: string) {
  const n = Number(raw);
  return raw.trim() && Number.isFinite(n) && n > 1 ? n : null;
}

function parseIntField(raw: string, fallback = 0) {
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : fallback;
}

function toLiveState(values: MatchFormValues): LiveState | null {
  if (!values.inPlay) return null;
  return {
    minute: Number(values.minute) || 0,
    homeGoals: parseIntField(values.homeGoals),
    awayGoals: parseIntField(values.awayGoals),
    redCardsHome: parseIntField(values.redHome),
    redCardsAway: parseIntField(values.redAway),
  };
}

function toAnalysisInput(values: MatchFormValues) {
  return {
    home: values.home,
    away: values.away,
    homeOdds: parseOdds(values.homeOdds),
    drawOdds: parseOdds(values.drawOdds),
    awayOdds: parseOdds(values.awayOdds),
    neutral: values.neutral,
    liveState: toLiveState(values),
  };
}

function marketsFromFixture(fixture: FwcFixture | null): SiblingMarkets | null {
  if (!fixture?.siblings) return null;
  return fixture.siblings;
}

function buildSiblingMarkets(
  values: MatchFormValues,
  fixture: FwcFixture | null,
): SiblingMarkets {
  const base = marketsFromFixture(fixture);
  return {
    eventSlug: fixture?.slug ?? "",
    home: values.home,
    away: values.away,
    homeOdds: parseOdds(values.homeOdds),
    drawOdds: parseOdds(values.drawOdds),
    awayOdds: parseOdds(values.awayOdds),
    totals: base?.totals ?? [],
    btts: base?.btts ?? null,
    correctScores: base?.correctScores ?? [],
  };
}

interface LiveSnapshot {
  minute: number;
  homeGoals: number;
  awayGoals: number;
  redCardsHome: number;
  redCardsAway: number;
  statusState: string;
  statusDetail: string;
  statusName: string;
  isLive: boolean;
  isFinal: boolean;
}

interface LiveApiResponse {
  home: string;
  away: string;
  siblingMarkets: SiblingMarkets;
  live: LiveSnapshot | null;
  status: "live" | "no_live_state";
  fetchedAt: string;
  error?: string;
}

const LIVE_REFRESH_MS = 20_000;

export default function HomePage() {
  const [analysis, setAnalysis] = useState<MatchAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fixtures, setFixtures] = useState<FwcFixture[]>([]);
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [fixturesError, setFixturesError] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<MatchFormValues>(FALLBACK_FORM);
  const [siblingMarkets, setSiblingMarkets] = useState<SiblingMarkets | null>(null);
  const [liveAuto, setLiveAuto] = useState(false);
  const [liveMeta, setLiveMeta] = useState<{
    live: LiveSnapshot;
    fetchedAt: string;
  } | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);

  const runAnalysis = useCallback(
    (values: MatchFormValues, fixture: FwcFixture | null = null) => {
      setLoading(true);
      setError(null);
      try {
        const result = analyzeMatch(toAnalysisInput(values));
        setAnalysis(result);

        const markets = buildSiblingMarkets(values, fixture);
        setSiblingMarkets(markets);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Analysis failed");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const fetchLiveAndAnalyze = useCallback(
    async (slug: string): Promise<LiveApiResponse | null> => {
      try {
        const response = await fetch(
          `/api/live?slug=${encodeURIComponent(slug)}`,
          { cache: "no-store" },
        );
        const payload = (await response.json()) as LiveApiResponse;
        if (!response.ok) {
          throw new Error(payload.error ?? "Live fetch failed");
        }

        const markets = payload.siblingMarkets;
        const live = payload.live;
        if (!live) {
          setLiveMeta(null);
          setLiveError(
            "No live match state yet — pre-match, or not on the ESPN scoreboard.",
          );
          return payload;
        }

        const values: MatchFormValues = {
          home: payload.home,
          away: payload.away,
          homeOdds: markets.homeOdds != null ? String(markets.homeOdds) : "",
          drawOdds: markets.drawOdds != null ? String(markets.drawOdds) : "",
          awayOdds: markets.awayOdds != null ? String(markets.awayOdds) : "",
          neutral: true,
          inPlay: true,
          minute: String(Math.round(live.minute)),
          homeGoals: String(live.homeGoals),
          awayGoals: String(live.awayGoals),
          redHome: String(live.redCardsHome),
          redAway: String(live.redCardsAway),
        };
        setFormValues(values);
        setLiveError(null);
        setLiveMeta({ live, fetchedAt: payload.fetchedAt });

        try {
          setAnalysis(analyzeMatch(toAnalysisInput(values)));
          setSiblingMarkets(markets);
          setError(null);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Analysis failed");
        }
        return payload;
      } catch (err) {
        setLiveError(err instanceof Error ? err.message : "Live fetch failed");
        return null;
      }
    },
    [],
  );

  const applyFixture = useCallback(
    (fixture: FwcFixture, analyze = true) => {
      const values = fixtureToFormValues(fixture);
      setSelectedSlug(fixture.slug);
      setFormValues(values);
      if (analyze) runAnalysis(values, fixture);
    },
    [runAnalysis],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadFixtures() {
      setFixturesLoading(true);
      setFixturesError(null);
      try {
        const response = await fetch("/api/fixtures");
        const payload = (await response.json()) as {
          fixtures?: FwcFixture[];
          defaultSlug?: string | null;
          error?: string;
        };

        if (!response.ok) {
          throw new Error(payload.error ?? "Failed to load fixtures");
        }

        if (cancelled) return;

        const loaded = payload.fixtures ?? [];
        setFixtures(loaded);

        const defaultFixture =
          loaded.find((f) => f.slug === payload.defaultSlug) ??
          pickDefaultFixture(loaded);

        if (defaultFixture) {
          applyFixture(defaultFixture);
        } else {
          runAnalysis(FALLBACK_FORM, null);
        }
      } catch (err) {
        if (cancelled) return;
        setFixturesError(
          err instanceof Error ? err.message : "Could not load World Cup fixtures",
        );
        runAnalysis(FALLBACK_FORM, null);
      } finally {
        if (!cancelled) setFixturesLoading(false);
      }
    }

    void loadFixtures();
    return () => {
      cancelled = true;
    };
  }, [applyFixture, runAnalysis]);

  // Live auto-refresh: poll ESPN state + Polymarket odds while enabled.
  useEffect(() => {
    if (!liveAuto || !selectedSlug) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      const payload = await fetchLiveAndAnalyze(selectedSlug);
      if (cancelled) return;
      if (payload?.live?.isFinal) {
        setLiveAuto(false); // match over — stop polling
        return;
      }
      timer = setTimeout(() => void tick(), LIVE_REFRESH_MS);
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [liveAuto, selectedSlug, fetchLiveAndAnalyze]);

  const edgeSweepResult =
    analysis && siblingMarkets && analysis.scorelineMatrix
      ? edgeSweep(
          analysis.scorelineMatrix,
          siblingMarkets,
          {
            home: analysis.pHome,
            draw: analysis.pDraw,
            away: analysis.pAway,
          },
        )
      : null;

  const locks = siblingMarkets ? detectLocks(siblingMarkets) : [];

  const activeFixture = fixtures.find((f) => f.slug === selectedSlug) ?? null;

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8 text-center sm:mb-10">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Phase 0 · Dixon-Coles + Elo · In-play
        </div>
        <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
          fv-match
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-balance text-sm leading-relaxed text-[var(--muted)] sm:text-base">
          Football match-outcome fair value. Model H/D/A probabilities, de-vig market
          prices, cross-market edge sweep, and fractional Kelly — CLV-validated before
          any live capital.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_1fr] lg:items-start">
        <MatchForm
          fixtures={fixtures}
          fixturesError={fixturesError}
          fixturesLoading={fixturesLoading}
          loading={loading}
          selectedSlug={selectedSlug}
          values={formValues}
          onChange={setFormValues}
          onFixtureSelect={(fixture) => applyFixture(fixture, true)}
          onSubmit={(values) => {
            setFormValues(values);
            runAnalysis(values, activeFixture);
          }}
        />

        <div className="min-w-0 space-y-5">
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}
          <LiveControls
            enabled={liveAuto}
            disabled={!selectedSlug}
            meta={liveMeta}
            error={liveError}
            onToggle={() => {
              setLiveError(null);
              setLiveAuto((v) => !v);
            }}
          />
          {analysis ? (
            <>
              <AnalysisResults analysis={analysis} />
              <EdgeArbTables edgeSweep={edgeSweepResult} locks={locks} />
            </>
          ) : (
            <div className="glass flex min-h-[320px] items-center justify-center rounded-2xl text-sm text-[var(--muted)]">
              {fixturesLoading ? "Loading World Cup fixtures…" : "Select a match to analyze"}
            </div>
          )}
        </div>
      </div>

      <footer className="mt-10 border-t border-[var(--border)] pt-6 text-center text-xs text-[var(--muted)]">
        Model-only demo. DRY_RUN enforced — no orders placed. Beat the close.
      </footer>
    </main>
  );
}

function LiveControls({
  enabled,
  disabled,
  meta,
  error,
  onToggle,
}: {
  enabled: boolean;
  disabled: boolean;
  meta: { live: LiveSnapshot; fetchedAt: string } | null;
  error: string | null;
  onToggle: () => void;
}) {
  const live = meta?.live ?? null;
  const updated = meta?.fetchedAt
    ? new Date(meta.fetchedAt).toLocaleTimeString()
    : null;

  return (
    <div className="glass flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[var(--border)] px-4 py-3">
      <div className="flex items-center gap-3">
        <button
          className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
            enabled
              ? "bg-red-500/90 text-white hover:bg-red-500"
              : "bg-cyan-500/90 text-cyan-950 hover:bg-cyan-400"
          }`}
          disabled={disabled}
          type="button"
          onClick={onToggle}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              enabled ? "animate-pulse bg-white" : "bg-cyan-950"
            }`}
          />
          {enabled ? "Stop live" : "Go live (auto)"}
        </button>
        <div className="text-sm text-[var(--muted)]">
          {disabled ? (
            "Select a World Cup fixture to enable live auto-refresh"
          ) : enabled ? (
            live ? (
              <span>
                <span className="font-semibold text-cyan-300">
                  {live.statusDetail || `${Math.round(live.minute)}'`} ·{" "}
                  {live.homeGoals}-{live.awayGoals}
                </span>
                {live.redCardsHome || live.redCardsAway ? (
                  <span>
                    {" "}
                    · reds {live.redCardsHome}-{live.redCardsAway}
                  </span>
                ) : null}
                {live.isFinal ? <span> · FT (stopped)</span> : null}
              </span>
            ) : (
              "Waiting for live match state…"
            )
          ) : (
            "Pulls ESPN score/minute + Polymarket odds every 20s"
          )}
        </div>
      </div>
      <div className="text-right text-xs text-[var(--muted)]">
        {error ? (
          <span className="text-amber-300/90">{error}</span>
        ) : updated && enabled ? (
          <span>updated {updated} · auto 20s · DRY-RUN</span>
        ) : null}
      </div>
    </div>
  );
}
