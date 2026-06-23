import { DEFAULT_CONFIG, OUTCOMES, type Outcome } from "./constants";
import { devig } from "./devig";
import { filterLegs } from "./gate";
import { jointMatchStakes, type Leg } from "./kelly";
import { getRating } from "./ratings";

const GOAL_FLOOR = 0.02;

export interface OutcomeView {
  outcome: Outcome;
  modelP: number;
  fairOdds: number;
  marketPrice: number | null;
  marketOdds: number | null;
  consensusP: number | null;
  edge: number | null;
  evPerDollar: number | null;
  stakeFraction: number;
  stakeUsd: number;
  bet: boolean;
}

export interface MatchAnalysis {
  home: string;
  away: string;
  neutral: boolean;
  eloHome: number;
  eloAway: number;
  lamHome: number;
  lamAway: number;
  pHome: number;
  pDraw: number;
  pAway: number;
  expectedHomeGoals: number;
  expectedAwayGoals: number;
  overround: number | null;
  outcomes: OutcomeView[];
  topScorelines: Array<{ home: number; away: number; p: number }>;
  dryRun: boolean;
  hasBets: boolean;
}

export interface AnalyzeInput {
  home: string;
  away: string;
  homeOdds?: number | null;
  drawOdds?: number | null;
  awayOdds?: number | null;
  neutral?: boolean;
  eloHome?: number | null;
  eloAway?: number | null;
}

function logFactorial(n: number): number {
  if (n <= 1) return 0;
  let result = 0;
  for (let i = 2; i <= n; i += 1) {
    result += Math.log(i);
  }
  return result;
}

function lambdasFromElo(
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

function tau(
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

function poissonPmf(lam: number, maxGoals: number): number[] {
  const pmf: number[] = [];
  for (let k = 0; k <= maxGoals; k += 1) {
    const logPmf = -lam + k * Math.log(lam) - logFactorial(k);
    pmf.push(Math.exp(logPmf));
  }
  return pmf;
}

function scorelineMatrix(
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

function marginalHda(matrix: number[][]): [number, number, number] {
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

function topScorelines(matrix: number[][], n = 6) {
  const flat: Array<{ home: number; away: number; p: number }> = [];
  for (let i = 0; i < matrix.length; i += 1) {
    for (let j = 0; j < matrix[i].length; j += 1) {
      flat.push({ home: i, away: j, p: matrix[i][j] });
    }
  }
  flat.sort((a, b) => b.p - a.p);
  return flat.slice(0, n);
}

function validOdds(odds?: number | null): odds is number {
  return typeof odds === "number" && odds > 1;
}

export function analyzeMatch(input: AnalyzeInput): MatchAnalysis {
  const {
    home,
    away,
    homeOdds,
    drawOdds,
    awayOdds,
    neutral = true,
    eloHome: eloHomeOverride,
    eloAway: eloAwayOverride,
  } = input;

  const eh = eloHomeOverride ?? getRating(home);
  const ea = eloAwayOverride ?? getRating(away);
  const homeAdv = neutral ? 0 : DEFAULT_CONFIG.homeAdvantageElo;

  const [lamHome, lamAway] = lambdasFromElo(eh, ea, homeAdv);
  const matrix = scorelineMatrix(lamHome, lamAway);
  const [pHome, pDraw, pAway] = marginalHda(matrix);
  const modelPs: Record<Outcome, number> = { home: pHome, draw: pDraw, away: pAway };

  const haveOdds =
    validOdds(homeOdds) && validOdds(drawOdds) && validOdds(awayOdds);

  const oddsMap: Record<Outcome, number> = {
    home: homeOdds ?? 0,
    draw: drawOdds ?? 0,
    away: awayOdds ?? 0,
  };

  let consensus: Record<Outcome, number> = { home: 0, draw: 0, away: 0 };
  let overround: number | null = null;
  let legs: Leg[] = [];

  if (haveOdds) {
    const ordered = OUTCOMES.map((o) => oddsMap[o]);
    const devigged = devig(ordered, DEFAULT_CONFIG.devigMethod);
    OUTCOMES.forEach((o, idx) => {
      consensus[o] = devigged[idx];
    });
    overround = ordered.reduce((acc, o) => acc + 1 / o, 0) - 1;
    legs = OUTCOMES.map((o) => ({
      outcome: o,
      p: modelPs[o],
      price: 1 / oddsMap[o],
    }));
  }

  const kept = haveOdds ? filterLegs(legs, DEFAULT_CONFIG.edgeThreshold) : [];
  const stakeFracs = kept.length
    ? jointMatchStakes(kept, DEFAULT_CONFIG.kellyFraction, DEFAULT_CONFIG.kellyCap)
    : [];
  const stakeByOutcome = Object.fromEntries(
    kept.map((leg, idx) => [leg.outcome, stakeFracs[idx]]),
  );

  const outcomes: OutcomeView[] = OUTCOMES.map((o) => {
    const mp = modelPs[o];
    if (haveOdds) {
      const odds = oddsMap[o];
      const price = 1 / odds;
      const cons = consensus[o];
      const edge = mp - cons;
      const ev = mp / price - 1;
      const frac = stakeByOutcome[o] ?? 0;
      return {
        outcome: o,
        modelP: mp,
        fairOdds: mp > 0 ? 1 / mp : Infinity,
        marketPrice: price,
        marketOdds: odds,
        consensusP: cons,
        edge,
        evPerDollar: ev,
        stakeFraction: frac,
        stakeUsd: frac * DEFAULT_CONFIG.bankroll,
        bet: frac > 0,
      };
    }
    return {
      outcome: o,
      modelP: mp,
      fairOdds: mp > 0 ? 1 / mp : Infinity,
      marketPrice: null,
      marketOdds: null,
      consensusP: null,
      edge: null,
      evPerDollar: null,
      stakeFraction: 0,
      stakeUsd: 0,
      bet: false,
    };
  });

  return {
    home,
    away,
    neutral,
    eloHome: eh,
    eloAway: ea,
    lamHome,
    lamAway,
    pHome,
    pDraw,
    pAway,
    expectedHomeGoals: lamHome,
    expectedAwayGoals: lamAway,
    overround,
    outcomes,
    topScorelines: topScorelines(matrix),
    dryRun: DEFAULT_CONFIG.dryRun,
    hasBets: outcomes.some((o) => o.bet),
  };
}
