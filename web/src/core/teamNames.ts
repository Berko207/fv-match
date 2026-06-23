/** Map Polymarket / FIFA display names to bundled Elo rating keys. */
const TEAM_ALIASES: Record<string, string> = {
  "korea republic": "South Korea",
  türkiye: "Turkey",
  turkey: "Turkey",
  "côte d'ivoire": "Ivory Coast",
  "cote d'ivoire": "Ivory Coast",
  "cabo verde": "Cape Verde",
  curaçao: "Curacao",
  curacao: "Curacao",
  "bosnia-herzegovina": "Bosnia and Herzegovina",
  "ir iran": "Iran",
  "united states": "USA",
};

export function normalizeTeamName(raw: string): string {
  const trimmed = raw.trim();
  const alias = TEAM_ALIASES[trimmed.toLowerCase()];
  return alias ?? trimmed;
}
