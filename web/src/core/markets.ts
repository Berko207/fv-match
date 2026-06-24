export interface TotalsMarket {
  line: number;
  overOdds: number | null;
  underOdds: number | null;
}

export interface BttsMarket {
  yesOdds: number | null;
  noOdds: number | null;
}

export interface CorrectScoreMarket {
  homeGoals: number;
  awayGoals: number;
  odds: number | null;
}

/** Parsed sibling markets for one fixture (moneyline + props). */
export interface SiblingMarkets {
  eventSlug: string;
  home: string;
  away: string;
  homeOdds: number | null;
  drawOdds: number | null;
  awayOdds: number | null;
  totals: TotalsMarket[];
  btts: BttsMarket | null;
  correctScores: CorrectScoreMarket[];
}
