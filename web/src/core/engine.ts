import { DEFAULT_CONFIG, OUTCOMES, type Outcome } from "./constants";
import {
  lambdasFromElo,
  marginalHda,
  scorelineMatrix,
  topScorelines,
  validOdds,
} from "./dixonColes";
import { devig } from "./devig";
import { filterLegs } from "./gate";
import { jointMatchStakes, type Leg } from "./kelly";
import { conditionalScorelineMatrix, type LiveState } from "./live";
import { getRating } from "./ratings";

export {
  lambdasFromElo,
  logFactorial,
  marginalHda,
  poissonPmf,
  scorelineMatrix,
  tau,
  topScorelines,
  validOdds,
} from "./dixonColes";

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
  liveState?: LiveState | null;
  scorelineMatrix?: number[][];
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
  liveState?: LiveState | null;
}

function buildOutcomeViews(
  modelPs: Record<Outcome, number>,
  haveOdds: boolean,
  oddsMap: Record<Outcome, number>,
  consensus: Record<Outcome, number>,
  kept: Leg[],
  stakeFracs: number[],
): OutcomeView[] {
  const stakeByOutcome = Object.fromEntries(
    kept.map((leg, idx) => [leg.outcome, stakeFracs[idx]]),
  );

  return OUTCOMES.map((o) => {
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
}

function runAnalysisCore(
  input: AnalyzeInput,
  matrix: number[][],
  lamHome: number,
  lamAway: number,
  eh: number,
  ea: number,
): MatchAnalysis {
  const {
    home,
    away,
    homeOdds,
    drawOdds,
    awayOdds,
    neutral = true,
    liveState = null,
  } = input;

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
  const outcomes = buildOutcomeViews(
    modelPs,
    haveOdds,
    oddsMap,
    consensus,
    kept,
    stakeFracs,
  );

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
    liveState,
    scorelineMatrix: matrix,
  };
}

export function analyzeMatch(input: AnalyzeInput): MatchAnalysis {
  const {
    home,
    away,
    neutral = true,
    eloHome: eloHomeOverride,
    eloAway: eloAwayOverride,
    liveState,
  } = input;

  const eh = eloHomeOverride ?? getRating(home);
  const ea = eloAwayOverride ?? getRating(away);
  const homeAdv = neutral ? 0 : DEFAULT_CONFIG.homeAdvantageElo;
  const [lamHome, lamAway] = lambdasFromElo(eh, ea, homeAdv);

  const matrix =
    liveState != null
      ? conditionalScorelineMatrix(lamHome, lamAway, liveState)
      : scorelineMatrix(lamHome, lamAway);

  return runAnalysisCore(input, matrix, lamHome, lamAway, eh, ea);
}

/** Explicit in-play entry point (same pipeline, conditional matrix). */
export function analyzeLiveMatch(
  input: AnalyzeInput & { liveState: LiveState },
): MatchAnalysis {
  return analyzeMatch(input);
}
