import { DEFAULT_CONFIG } from "./constants";

const GOAL_FLOOR = 0.02;

export function logFactorial(n: number): number {
  if (n <= 1) return 0;
  let result = 0;
  for (let i = 2; i <= n; i += 1) {
    result += Math.log(i);
  }
  return result;
}

export function lambdasFromElo(
  eloHome: number,
  eloAway: number,
  homeAdvantage = DEFAULT_CONFIG.homeAdvantageElo,
  baseGoals = DEFAULT_CONFIG.baseGoals,
  goalScale = DEFAULT_CONFIG.eloGoalScale,
): [number, number] {
  const supremacy = (eloHome + homeAdvantage - eloAway) / goalScale;
  const lamHome = Math.max((baseGoals + supremacy) / 2, GOAL_FLOOR);
  const lamAway = Math.max((baseGoals - supremacy) / 2, GOAL_FLOOR);
  return [lamHome, lamAway];
}

export function tau(
  i: number,
  j: number,
  lamHome: number,
  lamAway: number,
  rho: number,
): number {
  if (i === 0 && j === 0) return 1 - lamHome * lamAway * rho;
  if (i === 0 && j === 1) return 1 + lamHome * rho;
  if (i === 1 && j === 0) return 1 + lamAway * rho;
  if (i === 1 && j === 1) return 1 - rho;
  return 1;
}

export function poissonPmf(lam: number, maxGoals: number): number[] {
  const pmf: number[] = [];
  for (let k = 0; k <= maxGoals; k += 1) {
    const logPmf = -lam + k * Math.log(lam) - logFactorial(k);
    pmf.push(Math.exp(logPmf));
  }
  return pmf;
}

export function scorelineMatrix(
  lamHome: number,
  lamAway: number,
  rho = DEFAULT_CONFIG.dcRho,
  maxGoals = DEFAULT_CONFIG.maxGoals,
): number[][] {
  const homePmf = poissonPmf(lamHome, maxGoals);
  const awayPmf = poissonPmf(lamAway, maxGoals);
  const matrix: number[][] = Array.from({ length: maxGoals + 1 }, () =>
    Array(maxGoals + 1).fill(0),
  );

  for (let i = 0; i <= maxGoals; i += 1) {
    for (let j = 0; j <= maxGoals; j += 1) {
      matrix[i][j] = homePmf[i] * awayPmf[j];
    }
  }

  for (const i of [0, 1]) {
    for (const j of [0, 1]) {
      matrix[i][j] *= tau(i, j, lamHome, lamAway, rho);
    }
  }

  let total = 0;
  for (let i = 0; i <= maxGoals; i += 1) {
    for (let j = 0; j <= maxGoals; j += 1) {
      matrix[i][j] = Math.max(0, matrix[i][j]);
      total += matrix[i][j];
    }
  }

  if (total <= 0) throw new Error("Degenerate scoreline matrix");
  for (let i = 0; i <= maxGoals; i += 1) {
    for (let j = 0; j <= maxGoals; j += 1) {
      matrix[i][j] /= total;
    }
  }
  return matrix;
}

export function marginalHda(matrix: number[][]): [number, number, number] {
  let pHome = 0;
  let pDraw = 0;
  let pAway = 0;
  for (let i = 0; i < matrix.length; i += 1) {
    for (let j = 0; j < matrix[i].length; j += 1) {
      if (i > j) pHome += matrix[i][j];
      else if (i === j) pDraw += matrix[i][j];
      else pAway += matrix[i][j];
    }
  }
  return [pHome, pDraw, pAway];
}

export function topScorelines(matrix: number[][], n = 6) {
  const flat: Array<{ home: number; away: number; p: number }> = [];
  for (let i = 0; i < matrix.length; i += 1) {
    for (let j = 0; j < matrix[i].length; j += 1) {
      flat.push({ home: i, away: j, p: matrix[i][j] });
    }
  }
  flat.sort((a, b) => b.p - a.p);
  return flat.slice(0, n);
}

export function validOdds(odds?: number | null): odds is number {
  return typeof odds === "number" && odds > 1;
}
