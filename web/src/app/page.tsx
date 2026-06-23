"use client";

import { useCallback, useEffect, useState } from "react";

import { AnalysisResults } from "@/components/AnalysisResults";
import { MatchForm, type MatchFormValues } from "@/components/MatchForm";
import {
  fixtureToFormValues,
  pickDefaultFixture,
  type FwcFixture,
} from "@/core/fixtures";
import type { MatchAnalysis } from "@/core/engine";
import { analyzeMatch } from "@/core/engine";

const FALLBACK_FORM: MatchFormValues = {
  home: "Portugal",
  away: "Uzbekistan",
  homeOdds: "",
  drawOdds: "",
  awayOdds: "",
  neutral: true,
};

function toAnalysisInput(values: MatchFormValues) {
  const parseOdds = (raw: string) => {
    const n = Number(raw);
    return raw.trim() && Number.isFinite(n) && n > 1 ? n : null;
  };

  return {
    home: values.home,
    away: values.away,
    homeOdds: parseOdds(values.homeOdds),
    drawOdds: parseOdds(values.drawOdds),
    awayOdds: parseOdds(values.awayOdds),
    neutral: values.neutral,
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

  const runAnalysis = useCallback((values: MatchFormValues) => {
    setLoading(true);
    setError(null);
    try {
      const result = analyzeMatch(toAnalysisInput(values));
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const applyFixture = useCallback(
    (fixture: FwcFixture, analyze = true) => {
      const values = fixtureToFormValues(fixture);
      setSelectedSlug(fixture.slug);
      setFormValues(values);
      if (analyze) runAnalysis(values);
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
          runAnalysis(FALLBACK_FORM);
        }
      } catch (err) {
        if (cancelled) return;
        setFixturesError(
          err instanceof Error ? err.message : "Could not load World Cup fixtures",
        );
        runAnalysis(FALLBACK_FORM);
      } finally {
        if (!cancelled) setFixturesLoading(false);
      }
    }

    void loadFixtures();
    return () => {
      cancelled = true;
    };
  }, [applyFixture, runAnalysis]);

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8 text-center sm:mb-10">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Phase 0 · Dixon-Coles + Elo
        </div>
        <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
          fv-match
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-balance text-sm leading-relaxed text-[var(--muted)] sm:text-base">
          Football match-outcome fair value. Model H/D/A probabilities, de-vig market
          prices, and surface +EV edges sized by fractional Kelly — CLV-validated before
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
            runAnalysis(values);
          }}
        />

        <div className="min-w-0">
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}
          {analysis ? (
            <AnalysisResults analysis={analysis} />
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
