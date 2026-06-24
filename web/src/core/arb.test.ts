import { describe, expect, it } from "vitest";

import { deriveMarketProbs, detectLocks, detectNWayLock, edgeSweep } from "./arb";
import { scorelineMatrix } from "./dixonColes";
import type { SiblingMarkets } from "./markets";

describe("deriveMarketProbs", () => {
  it("derives BTTS and totals from matrix", () => {
    const matrix = scorelineMatrix(1.4, 1.1, -0.08, 6);
    const derived = deriveMarketProbs(matrix);
    expect(derived.btts.yes + derived.btts.no).toBeCloseTo(1, 8);
    expect(derived.totals["2.5"].over + derived.totals["2.5"].under).toBeCloseTo(1, 8);
    expect(derived.correctScores.length).toBeGreaterThan(0);
  });
});

describe("detectNWayLock", () => {
  it("finds three-way moneyline lock", () => {
    const lock = detectNWayLock("ML", [
      { label: "Home", odds: 3.5 },
      { label: "Draw", odds: 4.0 },
      { label: "Away", odds: 5.0 },
    ]);
    expect(lock).not.toBeNull();
    expect(lock!.profitMargin).toBeGreaterThan(0);
    const stakeSum = lock!.legs.reduce((s, l) => s + l.stakeFraction, 0);
    expect(stakeSum).toBeCloseTo(1, 6);
  });

  it("returns null when no lock", () => {
    const lock = detectNWayLock("ML", [
      { label: "Home", odds: 1.5 },
      { label: "Draw", odds: 4.0 },
      { label: "Away", odds: 6.0 },
    ]);
    expect(lock).toBeNull();
  });
});

describe("edgeSweep", () => {
  it("computes moneyline edges", () => {
    const matrix = scorelineMatrix(1.5, 1.0, -0.08, 8);
    const [pHome, pDraw, pAway] = [
      matrix.reduce((s, row, i) => s + row.reduce((t, c, j) => t + (i > j ? c : 0), 0), 0),
      matrix.reduce((s, row, i) => s + (row[i] ?? 0), 0),
      matrix.reduce((s, row, i) => s + row.reduce((t, c, j) => t + (i < j ? c : 0), 0), 0),
    ];
    const markets: SiblingMarkets = {
      eventSlug: "test",
      home: "A",
      away: "B",
      homeOdds: 2.0,
      drawOdds: 3.5,
      awayOdds: 4.0,
      totals: [],
      btts: null,
      correctScores: [],
    };
    const result = edgeSweep(matrix, markets, {
      home: pHome,
      draw: pDraw,
      away: pAway,
    });
    expect(result.legs.length).toBe(3);
    expect(result.legs.every((l) => l.edge != null)).toBe(true);
  });
});

describe("detectLocks", () => {
  it("aggregates same-market locks", () => {
    const markets: SiblingMarkets = {
      eventSlug: "test",
      home: "A",
      away: "B",
      homeOdds: 3.5,
      drawOdds: 4.0,
      awayOdds: 5.0,
      totals: [{ line: 2.5, overOdds: 2.1, underOdds: 2.1 }],
      btts: null,
      correctScores: [],
    };
    const locks = detectLocks(markets);
    expect(locks.length).toBeGreaterThanOrEqual(1);
  });
});
