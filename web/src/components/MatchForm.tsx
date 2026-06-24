"use client";

import { useMemo } from "react";

import { formatKickoff, type FwcFixture } from "@/core/fixtures";
import { listTeams } from "@/core/ratings";

export interface MatchFormValues {
  home: string;
  away: string;
  homeOdds: string;
  drawOdds: string;
  awayOdds: string;
  neutral: boolean;
  inPlay: boolean;
  minute: string;
  homeGoals: string;
  awayGoals: string;
  redHome: string;
  redAway: string;
}

interface MatchFormProps {
  values: MatchFormValues;
  loading: boolean;
  fixtures?: FwcFixture[];
  fixturesLoading?: boolean;
  fixturesError?: string | null;
  selectedSlug?: string | null;
  onChange: (values: MatchFormValues) => void;
  onFixtureSelect?: (fixture: FwcFixture) => void;
  onSubmit: (values: MatchFormValues) => void;
}

const STATUS_LABEL: Record<FwcFixture["status"], string> = {
  live: "LIVE",
  upcoming: "Upcoming",
  finished: "Finished",
};

export function MatchForm({
  values,
  loading,
  fixtures = [],
  fixturesLoading = false,
  fixturesError = null,
  selectedSlug = null,
  onChange,
  onFixtureSelect,
  onSubmit,
}: MatchFormProps) {
  const teams = useMemo(() => listTeams(), []);

  function update<K extends keyof MatchFormValues>(key: K, value: MatchFormValues[K]) {
    onChange({ ...values, [key]: value });
  }

  function handleFixtureChange(slug: string) {
    const fixture = fixtures.find((f) => f.slug === slug);
    if (!fixture) return;
    onFixtureSelect?.(fixture);
  }

  return (
    <form
      className="glass rounded-2xl p-5 shadow-glow sm:p-6"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(values);
      }}
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Fixture</h2>
          <p className="text-sm text-[var(--muted)]">
            Elo prior → Dixon-Coles → de-vig edge
          </p>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--muted)]">
          <input
            checked={values.neutral}
            className="accent-emerald-400"
            type="checkbox"
            onChange={(e) => update("neutral", e.target.checked)}
          />
          Neutral venue
        </label>
      </div>

      {fixtures.length > 0 || fixturesLoading || fixturesError ? (
        <div className="mb-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              FIFA World Cup 2026
            </span>
            <select
              className="field"
              disabled={fixturesLoading || fixtures.length === 0}
              value={selectedSlug ?? ""}
              onChange={(e) => handleFixtureChange(e.target.value)}
            >
              {fixturesLoading ? (
                <option value="">Loading matches…</option>
              ) : (
                fixtures.map((fixture) => (
                  <option key={fixture.slug} value={fixture.slug}>
                    {formatFixtureOption(fixture)}
                  </option>
                ))
              )}
            </select>
          </label>
          {fixturesError ? (
            <p className="mt-2 text-xs text-amber-300/90">{fixturesError}</p>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Home / Team A">
          <input
            className="field"
            list="teams-list"
            placeholder="e.g. Portugal"
            required
            value={values.home}
            onChange={(e) => update("home", e.target.value)}
          />
        </Field>
        <Field label="Away / Team B">
          <input
            className="field"
            list="teams-list"
            placeholder="e.g. Uzbekistan"
            required
            value={values.away}
            onChange={(e) => update("away", e.target.value)}
          />
        </Field>
      </div>

      <datalist id="teams-list">
        {teams.map((team) => (
          <option key={team} value={team} />
        ))}
      </datalist>

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Field label="Home odds">
          <input
            className="field"
            inputMode="decimal"
            min="1.01"
            placeholder="1.28"
            step="0.01"
            type="number"
            value={values.homeOdds}
            onChange={(e) => update("homeOdds", e.target.value)}
          />
        </Field>
        <Field label="Draw odds">
          <input
            className="field"
            inputMode="decimal"
            min="1.01"
            placeholder="6.0"
            step="0.01"
            type="number"
            value={values.drawOdds}
            onChange={(e) => update("drawOdds", e.target.value)}
          />
        </Field>
        <Field label="Away odds">
          <input
            className="field"
            inputMode="decimal"
            min="1.01"
            placeholder="12.0"
            step="0.01"
            type="number"
            value={values.awayOdds}
            onChange={(e) => update("awayOdds", e.target.value)}
          />
        </Field>
      </div>

      <div className="mt-5 rounded-xl border border-[var(--border)] bg-black/20 p-4">
        <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
          <input
            checked={values.inPlay}
            className="accent-cyan-400"
            type="checkbox"
            onChange={(e) => update("inPlay", e.target.checked)}
          />
          In-play mode
        </label>
        {values.inPlay ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Field label="Minute">
              <input
                className="field"
                inputMode="decimal"
                min="0"
                max="120"
                step="1"
                type="number"
                value={values.minute}
                onChange={(e) => update("minute", e.target.value)}
              />
            </Field>
            <Field label="Home goals">
              <input
                className="field"
                inputMode="numeric"
                min="0"
                type="number"
                value={values.homeGoals}
                onChange={(e) => update("homeGoals", e.target.value)}
              />
            </Field>
            <Field label="Away goals">
              <input
                className="field"
                inputMode="numeric"
                min="0"
                type="number"
                value={values.awayGoals}
                onChange={(e) => update("awayGoals", e.target.value)}
              />
            </Field>
            <Field label="Red cards (H)">
              <input
                className="field"
                inputMode="numeric"
                min="0"
                type="number"
                value={values.redHome}
                onChange={(e) => update("redHome", e.target.value)}
              />
            </Field>
            <Field label="Red cards (A)">
              <input
                className="field"
                inputMode="numeric"
                min="0"
                type="number"
                value={values.redAway}
                onChange={(e) => update("redAway", e.target.value)}
              />
            </Field>
          </div>
        ) : null}
      </div>

      <button
        className="mt-5 w-full rounded-xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-emerald-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={loading}
        type="submit"
      >
        {loading ? "Analyzing…" : "Run analysis"}
      </button>

      <style jsx>{`
        .field {
          width: 100%;
          border-radius: 0.75rem;
          border: 1px solid var(--border);
          background: rgba(10, 14, 18, 0.8);
          padding: 0.65rem 0.85rem;
          color: var(--text);
          outline: none;
          transition: border-color 0.15s ease;
        }
        .field:focus {
          border-color: rgba(52, 211, 153, 0.6);
        }
      `}</style>
    </form>
  );
}

function formatFixtureOption(fixture: FwcFixture): string {
  const when = fixture.kickoffUtc ? formatKickoff(fixture.kickoffUtc) : "TBD";
  const status =
    fixture.status === "live" ? ` · ${STATUS_LABEL.live}` : "";
  return `${fixture.home} vs ${fixture.away} · ${when}${status}`;
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}
