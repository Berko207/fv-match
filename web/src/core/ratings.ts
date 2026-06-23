import eloSeed from "@/data/international_elo.json";

const DEFAULT_ELO = 1600;

const ratingsTable: Record<string, number> = eloSeed.ratings;
const normalizedLookup = Object.fromEntries(
  Object.entries(ratingsTable).map(([k, v]) => [k.trim().toLowerCase(), v]),
);

export function listTeams(): string[] {
  return Object.keys(ratingsTable).sort((a, b) => a.localeCompare(b));
}

export function getRating(team: string): number {
  if (team in ratingsTable) return ratingsTable[team];
  return normalizedLookup[team.trim().toLowerCase()] ?? DEFAULT_ELO;
}

export const ELO_META = eloSeed._meta;
