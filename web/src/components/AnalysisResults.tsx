import type { MatchAnalysis, OutcomeView } from "@/core/engine";

import { ColumnHelp } from "@/components/ColumnHelp";

interface AnalysisResultsProps {
  analysis: MatchAnalysis;
}

const COLUMN_HELP: Array<{
  key: string;
  label: string;
  align?: "left" | "right";
  help: string;
}> = [
  {
    key: "outcome",
    label: "Outcome",
    align: "left",
    help: "Match result: home win, draw, or away win (90 minutes + stoppage time).",
  },
  {
    key: "model",
    label: "Model",
    align: "right",
    help: "Model win probability from Dixon-Coles + Elo (our fair-value estimate).",
  },
  {
    key: "fair",
    label: "Fair",
    align: "right",
    help: "Fair decimal odds implied by the model: 1 ÷ model probability.",
  },
  {
    key: "market",
    label: "Market",
    align: "right",
    help: "Raw decimal odds from Polymarket (or your manual input) before removing vig.",
  },
  {
    key: "consensus",
    label: "Consensus",
    align: "right",
    help: "De-vigged market probability — the book’s implied true chance after margin is removed.",
  },
  {
    key: "edge",
    label: "Edge",
    align: "right",
    help: "Model % minus consensus %. Positive means the market may be underpricing this outcome.",
  },
  {
    key: "ev",
    label: "EV/$",
    align: "right",
    help: "Expected profit per $1 staked at the market price, using model probability.",
  },
  {
    key: "stake",
    label: "Stake",
    align: "right",
    help: "Fractional Kelly bet size (USD) on a $1,000 bankroll — only shown when edge clears the 3% gate.",
  },
];

export function AnalysisResults({ analysis }: AnalysisResultsProps) {
  const labels: Record<string, string> = {
    home: analysis.home,
    draw: "Draw",
    away: analysis.away,
  };

  const totalStake = analysis.outcomes.reduce((sum, o) => sum + o.stakeUsd, 0);

  return (
    <div className="space-y-5">
      <section className="glass overflow-hidden rounded-2xl shadow-glow">
        <div className="border-b border-[var(--border)] bg-gradient-to-r from-emerald-500/10 to-transparent px-5 py-5 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-emerald-400/90">
                Matchup
              </p>
              <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
                {analysis.home}
                <span className="mx-2 text-[var(--muted)] font-normal">vs</span>
                {analysis.away}
              </h2>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Elo {Math.round(analysis.eloHome)} – {Math.round(analysis.eloAway)}
                <span className="mx-2">·</span>
                xG {analysis.expectedHomeGoals.toFixed(2)} –{" "}
                {analysis.expectedAwayGoals.toFixed(2)}
                <span className="mx-2">·</span>
                {analysis.neutral ? "Neutral" : "Home advantage"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="safe">DRY RUN</Badge>
              {analysis.overround != null && (
                <Badge tone="warn">
                  Overround {(analysis.overround * 100).toFixed(1)}%
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-4 p-5 sm:grid-cols-3 sm:p-6">
          <ProbCard label={analysis.home} value={analysis.pHome} tone="home" />
          <ProbCard label="Draw" value={analysis.pDraw} tone="draw" />
          <ProbCard label={analysis.away} value={analysis.pAway} tone="away" />
        </div>
      </section>

      <section className="glass rounded-2xl p-5 sm:p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
          Model vs Market
        </h3>
        <div className="overflow-x-auto pb-1 pt-8">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                {COLUMN_HELP.map((col) => (
                  <ColumnHeader
                    key={col.key}
                    align={col.align}
                    help={col.help}
                    label={col.label}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {analysis.outcomes.map((row) => (
                <OutcomeRow key={row.outcome} label={labels[row.outcome]} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="glass rounded-2xl p-5 sm:p-6">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
            Probability comparison
          </h3>
          <div className="space-y-4">
            {analysis.outcomes.map((row) => (
              <CompareBar
                key={row.outcome}
                label={labels[row.outcome]}
                modelP={row.modelP}
                consensusP={row.consensusP}
              />
            ))}
          </div>
        </section>

        <section className="glass rounded-2xl p-5 sm:p-6">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
            Top scorelines
          </h3>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {analysis.topScorelines.map((s, idx) => (
              <div
                key={`${s.home}-${s.away}`}
                className="rounded-xl border border-[var(--border)] bg-black/20 px-3 py-2.5"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-lg font-semibold">
                    {s.home}-{s.away}
                  </span>
                  <span className="text-xs text-[var(--muted)]">#{idx + 1}</span>
                </div>
                <div className="mt-1 text-sm text-emerald-300">
                  {(s.p * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section
        className={`rounded-2xl border px-5 py-4 sm:px-6 ${
          analysis.hasBets
            ? "border-emerald-500/30 bg-emerald-500/10"
            : "border-[var(--border)] bg-black/20"
        }`}
      >
        {analysis.hasBets ? (
          <p className="text-sm">
            <span className="font-semibold text-emerald-300">Proposed exposure:</span>{" "}
            {`$${totalStake.toFixed(2)} on a $1,000 bankroll (fractional Kelly, edge-gated). No live orders — dry-run only.`}
          </p>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            No outcome clears the 3% edge gate. Model-only view or market is efficiently
            priced on these lines.
          </p>
        )}
      </section>
    </div>
  );
}

function ColumnHeader({
  label,
  help,
  align = "left",
}: {
  label: string;
  help: string;
  align?: "left" | "right";
}) {
  return (
    <th className={`pb-3 pr-3 last:pr-0 ${align === "right" ? "text-right" : ""}`}>
      <span
        className={`inline-flex max-w-full items-center gap-1.5 ${
          align === "right" ? "justify-end" : ""
        }`}
      >
        <span>{label}</span>
        <ColumnHelp help={help} />
      </span>
    </th>
  );
}

function ProbCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "home" | "draw" | "away";
}) {
  const colors = {
    home: "from-sky-500/20 to-transparent border-sky-500/20",
    draw: "from-amber-500/20 to-transparent border-amber-500/20",
    away: "from-violet-500/20 to-transparent border-violet-500/20",
  };

  return (
    <div
      className={`rounded-xl border bg-gradient-to-br p-4 ${colors[tone]}`}
    >
      <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-1 text-3xl font-bold tabular-nums">{(value * 100).toFixed(1)}%</p>
      <p className="mt-1 font-mono text-xs text-[var(--muted)]">
        fair {(value > 0 ? 1 / value : 0).toFixed(2)}
      </p>
    </div>
  );
}

function OutcomeRow({ label, row }: { label: string; row: OutcomeView }) {
  const edgePositive = row.edge != null && row.edge > 0;
  const edgeGated = row.edge != null && row.edge > 0.03;

  return (
    <tr className="border-b border-[var(--border)]/70 last:border-0">
      <td className="py-3 pr-3 font-medium">{label}</td>
      <td className="py-3 pr-3 text-right font-mono">{(row.modelP * 100).toFixed(1)}%</td>
      <td className="py-3 pr-3 text-right font-mono">
        {Number.isFinite(row.fairOdds) ? row.fairOdds.toFixed(2) : "—"}
      </td>
      <td className="py-3 pr-3 text-right font-mono">
        {row.marketOdds != null ? row.marketOdds.toFixed(2) : "—"}
      </td>
      <td className="py-3 pr-3 text-right font-mono">
        {row.consensusP != null ? `${(row.consensusP * 100).toFixed(1)}%` : "—"}
      </td>
      <td
        className={`py-3 pr-3 text-right font-mono ${
          edgeGated
            ? "text-emerald-300"
            : edgePositive
              ? "text-amber-300"
              : row.edge != null
                ? "text-red-300"
                : ""
        }`}
      >
        {row.edge != null ? `${(row.edge * 100).toFixed(1)}%` : "—"}
      </td>
      <td className="py-3 pr-3 text-right font-mono">
        {row.evPerDollar != null ? `${(row.evPerDollar * 100).toFixed(1)}%` : "—"}
      </td>
      <td className="py-3 text-right font-mono">
        {row.bet ? (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-emerald-300">
            ${row.stakeUsd.toFixed(2)}
          </span>
        ) : (
          "—"
        )}
      </td>
    </tr>
  );
}

function CompareBar({
  label,
  modelP,
  consensusP,
}: {
  label: string;
  modelP: number;
  consensusP: number | null;
}) {
  const max = Math.max(modelP, consensusP ?? 0, 0.01);

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span>{label}</span>
        <span className="font-mono text-xs text-[var(--muted)]">
          model {(modelP * 100).toFixed(1)}%
          {consensusP != null ? ` · mkt ${(consensusP * 100).toFixed(1)}%` : ""}
        </span>
      </div>
      <div className="space-y-1.5">
        <Bar color="bg-emerald-400" label="Model" value={modelP / max} />
        {consensusP != null && (
          <Bar color="bg-slate-400" label="Market" value={consensusP / max} />
        )}
      </div>
    </div>
  );
}

function Bar({
  color,
  label,
  value,
}: {
  color: string;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-12 text-[10px] uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-black/30">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${Math.max(2, value * 100)}%` }}
        />
      </div>
    </div>
  );
}

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "safe" | "warn";
}) {
  const styles =
    tone === "safe"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
      : "border-amber-500/30 bg-amber-500/10 text-amber-200";

  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${styles}`}
    >
      {children}
    </span>
  );
}
