import { describe, expect, it } from "vitest";

import { lambdasFromElo, marginalHda, scorelineMatrix } from "./dixonColes";
import {
  conditionalScorelineMatrix,
  liveHda,
  type LiveState,
} from "./live";

function fixtureLambdas(): [number, number] {
  return lambdasFromElo(1850, 1650, 0);
}

describe("conditionalScorelineMatrix", () => {
  it("matches pre-match at kickoff 0-0", () => {
    const [lamHome, lamAway] = fixtureLambdas();
    const rho = -0.08;
    const prematch = scorelineMatrix(lamHome, lamAway, rho, 10);
    const state: LiveState = { minute: 0, homeGoals: 0, awayGoals: 0 };
    const live = conditionalScorelineMatrix(
      lamHome,
      lamAway,
      state,
      rho,
      10,
      "uniform",
    );
    for (let i = 0; i <= 10; i += 1) {
      for (let j = 0; j <= 10; j += 1) {
        expect(live[i][j]).toBeCloseTo(prematch[i][j], 10);
      }
    }
  });

  it("late home lead dominates", () => {
    const [lamHome, lamAway] = fixtureLambdas();
    const prematch = marginalHda(scorelineMatrix(lamHome, lamAway, -0.08, 10));
    const state: LiveState = { minute: 80, homeGoals: 1, awayGoals: 0 };
    const [pHome, , pAway] = liveHda(lamHome, lamAway, state, {
      rho: -0.08,
      intensityProfile: "rising",
    });
    expect(pHome).toBeGreaterThan(prematch[0] + 0.15);
    expect(pAway).toBeLessThan(prematch[2] * 0.5);
  });

  it("full time is point mass", () => {
    const [lamHome, lamAway] = fixtureLambdas();
    const state: LiveState = { minute: 90, homeGoals: 0, awayGoals: 0 };
    const matrix = conditionalScorelineMatrix(lamHome, lamAway, state);
    expect(matrix[0][0]).toBeCloseTo(1, 10);
    const [, pDraw] = liveHda(lamHome, lamAway, state);
    expect(pDraw).toBeCloseTo(1, 10);
  });

  it("matrix sums to 1 without NaNs", () => {
    const [lamHome, lamAway] = fixtureLambdas();
    for (const minute of [0, 45, 89.5, 90, 95]) {
      const state: LiveState = { minute, homeGoals: 0, awayGoals: 0 };
      const matrix = conditionalScorelineMatrix(lamHome, lamAway, state);
      let total = 0;
      for (const row of matrix) {
        for (const cell of row) {
          expect(Number.isNaN(cell)).toBe(false);
          total += cell;
        }
      }
      expect(total).toBeCloseTo(1, 8);
    }
  });
});
