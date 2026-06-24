export const DEFAULT_CONFIG = {
  baseGoals: 2.6,
  eloGoalScale: 150,
  homeAdvantageElo: 65,
  dcRho: -0.08,
  maxGoals: 10,
  edgeThreshold: 0.03,
  kellyFraction: 0.25,
  kellyCap: 0.05,
  bankroll: 1000,
  devigMethod: "shin" as const,
  dryRun: true,
  liveIntensityProfile: "rising" as const,
};

export const OUTCOMES = ["home", "draw", "away"] as const;
export type Outcome = (typeof OUTCOMES)[number];

export type DevigMethod = "multiplicative" | "power" | "shin";
