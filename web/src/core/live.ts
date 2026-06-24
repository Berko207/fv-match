/**
 * In-play conditional scoreline model (TS port of Python live.py).
 * Remaining goals from pre-match lambdas, conditioned on minute/score/red cards.
 */

import { DEFAULT_CONFIG } from "./constants";
import { marginalHda, scorelineMatrix } from "./dixonColes";

/** Placeholder — tune vs historical in-play goal-rate curves. */
export const RISING_LATE_GAME_SLOPE = 0.3;
/** Placeholder — one man down ~25% fewer goals scored. */
export const RED_CARD_SELF = 0.75;
/** Placeholder — opponent modestly benefits from numerical advantage. */
export const RED_CARD_OPP = 1.1;

export interface LiveState {
  minute: number;
  homeGoals: number;
  awayGoals: number;
  redCardsHome?: number;
  redCardsAway?: number;
  matchLength?: number;
}

function clampMinute(minute: number, matchLength: number): number {
  return Math.min(Math.max(minute, 0), matchLength);
}

function remainingFraction(
  minute: number,
  matchLength: number,
  intensityProfile: string,
): number {
  if (matchLength <= 0) return 0;
  const u0 = clampMinute(minute, matchLength) / matchLength;
  const remainingTime = 1 - u0;
  if (remainingTime <= 0) return 0;
  if (intensityProfile === "uniform") return remainingTime;
  if (intensityProfile === "rising") {
    const slope = RISING_LATE_GAME_SLOPE;
    const fullWeight = 1 + slope / 2;
    const remainingWeight = remainingTime + (slope * (1 - u0 ** 2)) / 2;
    return remainingWeight / fullWeight;
  }
  throw new Error(
    `intensityProfile must be 'uniform' or 'rising', got ${intensityProfile}`,
  );
}

function redCardFactors(state: LiveState): [number, number] {
  const rh = state.redCardsHome ?? 0;
  const ra = state.redCardsAway ?? 0;
  const homeFactor = RED_CARD_SELF ** rh * RED_CARD_OPP ** ra;
  const awayFactor = RED_CARD_SELF ** ra * RED_CARD_OPP ** rh;
  return [homeFactor, awayFactor];
}

function pointMassMatrix(
  homeGoals: number,
  awayGoals: number,
  maxGoals: number,
): number[][] {
  const size = maxGoals + 1;
  const matrix = Array.from({ length: size }, () => Array(size).fill(0));
  const i = Math.min(homeGoals, maxGoals);
  const j = Math.min(awayGoals, maxGoals);
  matrix[i][j] = 1;
  return matrix;
}

function shiftRemainingMatrix(
  remaining: number[][],
  homeGoals: number,
  awayGoals: number,
  maxGoals: number,
): number[][] {
  const size = maxGoals + 1;
  const final = Array.from({ length: size }, () => Array(size).fill(0));
  for (let i = 0; i < remaining.length; i += 1) {
    for (let j = 0; j < remaining[i].length; j += 1) {
      const mass = remaining[i][j];
      if (mass <= 0) continue;
      let fi = homeGoals + i;
      let fj = awayGoals + j;
      if (fi >= size) fi = size - 1;
      if (fj >= size) fj = size - 1;
      final[fi][fj] += mass;
    }
  }
  let total = 0;
  for (let i = 0; i < size; i += 1) {
    for (let j = 0; j < size; j += 1) {
      total += final[i][j];
    }
  }
  if (total <= 0) throw new Error("Degenerate conditional scoreline matrix");
  for (let i = 0; i < size; i += 1) {
    for (let j = 0; j < size; j += 1) {
      final[i][j] /= total;
    }
  }
  return final;
}

export function conditionalScorelineMatrix(
  lamHome: number,
  lamAway: number,
  state: LiveState,
  rho = DEFAULT_CONFIG.dcRho,
  maxGoals = DEFAULT_CONFIG.maxGoals,
  intensityProfile: string = DEFAULT_CONFIG.liveIntensityProfile,
): number[][] {
  const matchLength = state.matchLength ?? 90;
  const minute = clampMinute(state.minute, matchLength);
  const f = remainingFraction(minute, matchLength, intensityProfile);

  if (f <= 0) {
    return pointMassMatrix(state.homeGoals, state.awayGoals, maxGoals);
  }

  const [redHome, redAway] = redCardFactors(state);
  const remainingLamHome = lamHome * f * redHome;
  const remainingLamAway = lamAway * f * redAway;

  // Dixon-Coles tau is a kickoff effect; remaining goals are ~Poisson in-play.
  const remainingRho = minute === 0 ? rho : 0;
  const remaining = scorelineMatrix(
    remainingLamHome,
    remainingLamAway,
    remainingRho,
    maxGoals,
  );
  return shiftRemainingMatrix(
    remaining,
    state.homeGoals,
    state.awayGoals,
    maxGoals,
  );
}

export function liveHda(
  lamHome: number,
  lamAway: number,
  state: LiveState,
  options?: {
    rho?: number;
    maxGoals?: number;
    intensityProfile?: string;
  },
): [number, number, number] {
  const matrix = conditionalScorelineMatrix(
    lamHome,
    lamAway,
    state,
    options?.rho,
    options?.maxGoals,
    options?.intensityProfile,
  );
  return marginalHda(matrix);
}
