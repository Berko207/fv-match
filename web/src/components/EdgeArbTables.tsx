"use client";

import type { ArbLock, EdgeSweepResult } from "@/core/arb";

interface EdgeArbTablesProps {
  edgeSweep: EdgeSweepResult | null;
  locks: ArbLock[];
}

export function EdgeArbTables({ edgeSweep, locks }: EdgeArbTablesProps) {
  if (!edgeSweep?.legs.length && !locks.length) return null;

  return (
    <div className="space-y-5">
      {edgeSweep && edgeSweep.legs.length > 0 ? (
        <section className="glass rounded-2xl p-5 sm:p-6">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
            Cross-market edge sweep
          </h3>
          <p className="mb-4 text-xs text-[var(--muted)]">
            Detector A — model vs de-vigged price across moneyline and sibling markets.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                  <th className="pb-2 pr-3">Market</th>
                  <th className="pb-2 pr-3">Side</th>
                  <th className="pb-2 pr-3 text-right">Model</th>
                  <th className="pb-2 pr-3 text-right">Mkt</th>
                  <th className="pb-2 pr-3 text-right">Edge</th>
                </tr>
              </thead>
              <tbody>
                {edgeSweep.legs
                  .filter((l) => l.marketOdds != null)
                  .map((leg) => (
                    <tr
                      key={`${leg.marketType}-${leg.label}-${leg.side}`}
                      className="border-b border-[var(--border)]/70 last:border-0"
                    >
                      <td className="py-2 pr-3">{leg.label}</td>
                      <td className="py-2 pr-3 capitalize">{leg.side}</td>
                      <td className="py-2 pr-3 text-right font-mono">
                        {(leg.modelP * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 pr-3 text-right font-mono">
                        {leg.marketOdds != null ? leg.marketOdds.toFixed(2) : "—"}
                      </td>
                      <td
                        className={`py-2 pr-3 text-right font-mono ${
                          leg.passesGate
                            ? "text-emerald-300"
                            : leg.edge != null && leg.edge > 0
                              ? "text-amber-300"
                              : leg.edge != null
                                ? "text-red-300"
                                : ""
                        }`}
                      >
                        {leg.edge != null ? `${(leg.edge * 100).toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {!edgeSweep.legs.some((l) => l.marketOdds != null && l.marketType !== "moneyline") && (
            <p className="mt-3 text-xs text-[var(--muted)]">
              No O/U, BTTS, or correct-score markets on Polymarket for this fixture yet —
              moneyline only.
            </p>
          )}
        </section>
      ) : null}

      {locks.length > 0 ? (
        <section className="glass rounded-2xl border border-amber-500/20 p-5 sm:p-6">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-amber-200">
            Same-market locks
          </h3>
          <p className="mb-4 text-xs text-[var(--muted)]">
            Implied prob sum &lt; 100% (pre-fees). Cross-market dutching needs server-side LP.
          </p>
          <div className="space-y-3">
            {locks.map((lock) => (
              <div
                key={lock.market}
                className="rounded-xl border border-[var(--border)] bg-black/20 px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{lock.market}</span>
                  <span className="text-sm text-amber-300">
                    +{(lock.profitMargin * 100).toFixed(2)}% margin
                  </span>
                </div>
                <ul className="mt-2 space-y-1 text-xs text-[var(--muted)]">
                  {lock.legs.map((leg) => (
                    <li key={leg.label}>
                      {leg.label} @ {leg.odds.toFixed(2)} — stake{" "}
                      {(leg.stakeFraction * 100).toFixed(1)}%
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
