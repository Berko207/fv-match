/**
 * Cross-market edge sweep (Detector A) and simple same-market lock checks.
 * Full cross-market LP arb solver is server-only — browser uses lock detection.
 */

import { DEFAULT_CONFIG } from "./constants";
import { devig } from "./devig";
import type { SiblingMarkets } from "./markets";

export interface DerivedProbs {
  totals: Record<string, { over: number; under: number }>;
  btts: { yes: number; no: number };
  correctScores: Array<{ home: number; away: number; p: number }>;
}

export interface EdgeLeg {
  marketType: "moneyline" | "totals" | "btts" | "correct_score";
  label: string;
  side: string;
  modelP: number;
  marketOdds: number | null;
  marketPrice: number | null;
  consensusP: number | null;
  edge: number | null;
  passesGate: boolean;
}

export interface EdgeSweepResult {
  legs: EdgeLeg[];
  positiveEdges: EdgeLeg[];
}

export interface ArbLockLeg {
  label: string;
  odds: number;
  stakeFraction: number;
}

export interface ArbLock {
  market: string;
  type: "two_way" | "three_way";
  legs: ArbLockLeg[];
  /** Guaranteed profit margin per $1 total stake (before fees). */
  profitMargin: number;
}

/** Derive totals, BTTS, and correct-score probs from a scoreline matrix. */
export function deriveMarketProbs(matrix: number[][]): DerivedProbs {
  const totals: Record<string, { over: number; under: number }> = {};
  const lines = [0.5, 1.5, 2.5, 3.5, 4.5];
  for (const line of lines) {
    let over = 0;
    for (let i = 0; i < matrix.length; i += 1) {
      for (let j = 0; j < matrix[i].length; j += 1) {
        if (i + j > line) over += matrix[i][j];
      }
    }
    totals[String(line)] = { over, under: 1 - over };
  }

  let bttsYes = 0;
  const correctScores: Array<{ home: number; away: number; p: number }> = [];
  for (let i = 0; i < matrix.length; i += 1) {
    for (let j = 0; j < matrix[i].length; j += 1) {
      const p = matrix[i][j];
      if (i >= 1 && j >= 1) bttsYes += p;
      if (p > 0.001) correctScores.push({ home: i, away: j, p });
    }
  }
  correctScores.sort((a, b) => b.p - a.p);

  return {
    totals,
    btts: { yes: bttsYes, no: 1 - bttsYes },
    correctScores,
  };
}

function priceToOdds(price: number | null): number | null {
  if (price == null || price <= 0) return null;
  const odds = 1 / price;
  return Number.isFinite(odds) && odds > 1 ? odds : null;
}

function pushLeg(
  legs: EdgeLeg[],
  leg: Omit<EdgeLeg, "passesGate" | "edge" | "consensusP"> & {
    edge?: number | null;
    consensusP?: number | null;
  },
  threshold: number,
): void {
  const edge = leg.edge ?? null;
  legs.push({
    ...leg,
    consensusP: leg.consensusP ?? null,
    edge,
    passesGate: edge != null && edge >= threshold,
  });
}

/**
 * Detector A — sweep model edge across moneyline + sibling markets.
 * This is the primary day-to-day signal surface.
 */
export function edgeSweep(
  matrix: number[][],
  markets: SiblingMarkets,
  modelHda: { home: number; draw: number; away: number },
  threshold = DEFAULT_CONFIG.edgeThreshold,
): EdgeSweepResult {
  const derived = deriveMarketProbs(matrix);
  const legs: EdgeLeg[] = [];

  const mlSides: Array<{ side: string; modelP: number; odds: number | null }> = [
    { side: "home", modelP: modelHda.home, odds: markets.homeOdds },
    { side: "draw", modelP: modelHda.draw, odds: markets.drawOdds },
    { side: "away", modelP: modelHda.away, odds: markets.awayOdds },
  ];
  const mlOdds = mlSides.map((s) => s.odds).filter((o): o is number => o != null && o > 1);
  const mlConsensus =
    mlOdds.length === 3
      ? devig(mlOdds, DEFAULT_CONFIG.devigMethod)
      : null;

  mlSides.forEach((s, idx) => {
    const odds = s.odds;
    const price = odds != null && odds > 1 ? 1 / odds : null;
    const consensusP = mlConsensus ? mlConsensus[idx] : null;
    pushLeg(legs, {
      marketType: "moneyline",
      label: "Moneyline",
      side: s.side,
      modelP: s.modelP,
      marketOdds: odds,
      marketPrice: price,
      consensusP,
      edge: consensusP != null ? s.modelP - consensusP : null,
    }, threshold);
  });

  for (const total of markets.totals) {
    const lineKey = String(total.line);
    const model = derived.totals[lineKey];
    if (!model) continue;
    const sides = [
      { side: "over", modelP: model.over, odds: total.overOdds },
      { side: "under", modelP: model.under, odds: total.underOdds },
    ];
    const oddsPair = sides.map((s) => s.odds).filter((o): o is number => o != null && o > 1);
    const consensus =
      oddsPair.length === 2 ? devig(oddsPair, DEFAULT_CONFIG.devigMethod) : null;
    sides.forEach((s, idx) => {
      const price = s.odds != null && s.odds > 1 ? 1 / s.odds : null;
      const consensusP = consensus ? consensus[idx] : null;
      pushLeg(legs, {
        marketType: "totals",
        label: `O/U ${total.line}`,
        side: s.side,
        modelP: s.modelP,
        marketOdds: s.odds,
        marketPrice: price,
        consensusP,
        edge: consensusP != null ? s.modelP - consensusP : null,
      }, threshold);
    });
  }

  if (markets.btts) {
    const bttsSides = [
      { side: "yes", modelP: derived.btts.yes, odds: markets.btts.yesOdds },
      { side: "no", modelP: derived.btts.no, odds: markets.btts.noOdds },
    ];
    const oddsPair = bttsSides.map((s) => s.odds).filter((o): o is number => o != null && o > 1);
    const consensus =
      oddsPair.length === 2 ? devig(oddsPair, DEFAULT_CONFIG.devigMethod) : null;
    bttsSides.forEach((s, idx) => {
      const price = s.odds != null && s.odds > 1 ? 1 / s.odds : null;
      const consensusP = consensus ? consensus[idx] : null;
      pushLeg(legs, {
        marketType: "btts",
        label: "BTTS",
        side: s.side,
        modelP: s.modelP,
        marketOdds: s.odds,
        marketPrice: price,
        consensusP,
        edge: consensusP != null ? s.modelP - consensusP : null,
      }, threshold);
    });
  }

  for (const cs of markets.correctScores) {
    const modelCell = derived.correctScores.find(
      (c) => c.home === cs.homeGoals && c.away === cs.awayGoals,
    );
    const modelP = modelCell?.p ?? 0;
    const price = cs.odds != null && cs.odds > 1 ? 1 / cs.odds : null;
    const consensusP = price;
    pushLeg(legs, {
      marketType: "correct_score",
      label: "Correct score",
      side: `${cs.homeGoals}-${cs.awayGoals}`,
      modelP,
      marketOdds: cs.odds,
      marketPrice: price,
      consensusP,
      edge: price != null ? modelP - price : null,
    }, threshold);
  }

  const positiveEdges = [...legs]
    .filter((l) => l.edge != null && l.edge > 0)
    .sort((a, b) => (b.edge ?? 0) - (a.edge ?? 0));

  return { legs, positiveEdges };
}

/** Simple n-way lock: sum of implied probs < 1 guarantees arb (pre-fees). */
export function detectNWayLock(
  market: string,
  outcomes: Array<{ label: string; odds: number }>,
): ArbLock | null {
  const valid = outcomes.filter((o) => o.odds > 1);
  if (valid.length < 2) return null;

  const impliedSum = valid.reduce((acc, o) => acc + 1 / o.odds, 0);
  if (impliedSum >= 1) return null;

  const profitMargin = 1 / impliedSum - 1;
  const legs: ArbLockLeg[] = valid.map((o) => ({
    label: o.label,
    odds: o.odds,
    stakeFraction: 1 / o.odds / impliedSum,
  }));

  return {
    market,
    type: valid.length === 2 ? "two_way" : "three_way",
    legs,
    profitMargin,
  };
}

/**
 * Same-market lock checks only (no cross-market LP).
 * Cross-market dutching needs a server-side LP solver.
 */
export function detectLocks(markets: SiblingMarkets): ArbLock[] {
  const locks: ArbLock[] = [];

  const ml = detectNWayLock("Moneyline", [
    { label: "Home", odds: markets.homeOdds ?? 0 },
    { label: "Draw", odds: markets.drawOdds ?? 0 },
    { label: "Away", odds: markets.awayOdds ?? 0 },
  ]);
  if (ml) locks.push(ml);

  for (const total of markets.totals) {
    const lock = detectNWayLock(`O/U ${total.line}`, [
      { label: "Over", odds: total.overOdds ?? 0 },
      { label: "Under", odds: total.underOdds ?? 0 },
    ]);
    if (lock) locks.push(lock);
  }

  if (markets.btts) {
    const lock = detectNWayLock("BTTS", [
      { label: "Yes", odds: markets.btts.yesOdds ?? 0 },
      { label: "No", odds: markets.btts.noOdds ?? 0 },
    ]);
    if (lock) locks.push(lock);
  }

  return locks;
}

export { priceToOdds };
