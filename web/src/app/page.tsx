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
