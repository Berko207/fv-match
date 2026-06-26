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

export type AnalysisSource = "fixture" | "manual" | "live";

interface MatchFormProps {
  values: MatchFormValues;
  loading: boolean;
  fixtures?: FwcFixture[];
  fixturesLoading?: boolean;
  fixturesError?: string | null;
  selectedSlug?: string | null;
  isDirty?: boolean;
  analysisSource?: AnalysisSource | null;
  lastUpdatedAt?: string | null;
  liveAuto?: boolean;
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
  isDirty = false,
  analysisSource = null,
  lastUpdatedAt = null,
  liveAuto = false,
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
          <h2 className="text-lg font-semibold tracking-tight">Inputs</h2>
          <p className="text-sm text-[var(--muted)]">
            Pick a fixture to auto-run · edit fields to override
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

      <div className="mb-5 rounded-xl border border-[var(--border)] bg-black/20 px-3 py-2.5 text-xs leading-relaxed text-[var(--muted)]">
        <span className="font-medium text-emerald-300/90">Pipeline</span>
        <span className="mx-1.5 text-[var(--border)]">·</span>
        Elo ratings → Dixon-Coles scoreline matrix → H/D/A fair % vs de-vigged
        Polymarket moneyline → edge + Kelly (read-only, DRY_RUN).
      </div>

      <InputStatus
        analysisSource={analysisSource}
        isDirty={isDirty}
        lastUpdatedAt={lastUpdatedAt}
        liveAuto={liveAuto}
        loading={loading}
      />

      {fixtures.length > 0 || fixturesLoading || fixturesError ? (
        <div className="mb-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              1 · Fixture <span className="normal-case text-[var(--muted)]/70">(auto-runs on change)</span>
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

      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        2 · Teams &amp; moneyline odds
      </p>

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
        <Field hint="Polymarket decimal" label="Home odds">
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
        <Field hint="Polymarket decimal" label="Draw odds">
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
        <Field hint="Polymarket decimal" label="Away odds">
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
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          3 · In-play state <span className="normal-case text-[var(--muted)]/70">(optional)</span>
        </p>
        <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
          <input
            checked={values.inPlay}
            className="accent-cyan-400"
            type="checkbox"
            onChange={(e) => update("inPlay", e.target.checked)}
          />
          Conditional on current score &amp; minute
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

      <div className="mt-5 space-y-2">
        <button
          className={`w-full rounded-xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed ${
            isDirty && !liveAuto
              ? "bg-emerald-500 text-emerald-950 hover:bg-emerald-400 disabled:opacity-60"
              : "border border-[var(--border)] bg-black/20 text-[var(--muted)] hover:border-emerald-500/30 hover:text-emerald-200 disabled:opacity-50"
          }`}
          disabled={loading || liveAuto || (!isDirty && !loading)}
          type="submit"
        >
          {loading
            ? "Recalculating…"
            : liveAuto
              ? "Live mode — auto-recalculating"
              : isDirty
                ? "Apply manual edits"
                : "Inputs match latest run"}
        </button>
        <p className="text-center text-[11px] leading-relaxed text-[var(--muted)]">
          {liveAuto
            ? "Turn off Go live to apply manual overrides."
            : isDirty
              ? "You changed fields since the last run — click to refresh the panel."
              : "Selecting a fixture runs the model automatically. Edit odds or in-play fields to enable this button."}
        </p>
      </div>

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

function InputStatus({
  isDirty,
  analysisSource,
  lastUpdatedAt,
  liveAuto,
  loading,
}: {
  isDirty: boolean;
  analysisSource: AnalysisSource | null;
  lastUpdatedAt: string | null;
  liveAuto: boolean;
  loading: boolean;
}) {
  const updated = lastUpdatedAt
    ? new Date(lastUpdatedAt).toLocaleTimeString()
    : null;

  const sourceLabel =
    liveAuto && analysisSource === "live"
      ? "Live feed"
      : analysisSource === "fixture"
        ? "Fixture load"
        : analysisSource === "manual"
          ? "Manual"
          : null;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      {loading ? (
        <StatusPill tone="neutral">Recalculating…</StatusPill>
      ) : isDirty ? (
        <StatusPill tone="warn">Unsaved edits</StatusPill>
      ) : (
        <StatusPill tone="ok">Synced</StatusPill>
      )}
      {sourceLabel ? <StatusPill tone="neutral">{sourceLabel}</StatusPill> : null}
      {updated ? (
        <span className="text-[11px] text-[var(--muted)]">last run {updated}</span>
      ) : null}
    </div>
  );
}

function StatusPill({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "ok" | "warn" | "neutral";
}) {
  const styles =
    tone === "ok"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
      : tone === "warn"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-200"
        : "border-[var(--border)] bg-black/20 text-[var(--muted)]";

  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${styles}`}
    >
      {children}
    </span>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline justify-between gap-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        <span>{label}</span>
        {hint ? <span className="normal-case text-[10px] text-[var(--muted)]/70">{hint}</span> : null}
      </span>
      {children}
    </label>
  );
}
