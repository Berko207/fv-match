import type { SiblingMarkets } from "./markets";

export type FixtureStatus = "upcoming" | "live" | "finished";

export interface FwcFixture {
  id: string;
  slug: string;
  label: string;
  home: string;
  away: string;
  kickoffUtc: string;
  status: FixtureStatus;
  homeOdds: number | null;
  drawOdds: number | null;
  awayOdds: number | null;
  closed: boolean;
  siblings?: SiblingMarkets;
}

function kickoffMs(fixture: FwcFixture): number {
  return new Date(fixture.kickoffUtc).getTime();
}

/** Prefer live, then nearest upcoming, then most recent kickoff. */
export function pickDefaultFixture(fixtures: FwcFixture[]): FwcFixture | null {
  if (!fixtures.length) return null;

  const live = fixtures
    .filter((f) => f.status === "live")
    .sort((a, b) => kickoffMs(b) - kickoffMs(a));
  if (live.length) return live[0];

  const upcoming = fixtures
    .filter((f) => f.status === "upcoming")
    .sort((a, b) => kickoffMs(a) - kickoffMs(b));
  if (upcoming.length) return upcoming[0];

  return [...fixtures].sort((a, b) => kickoffMs(b) - kickoffMs(a))[0];
}

export function fixtureToFormValues(fixture: FwcFixture) {
  const inPlay = fixture.status === "live";
  return {
    home: fixture.home,
    away: fixture.away,
    homeOdds: fixture.homeOdds != null ? String(fixture.homeOdds) : "",
    drawOdds: fixture.drawOdds != null ? String(fixture.drawOdds) : "",
    awayOdds: fixture.awayOdds != null ? String(fixture.awayOdds) : "",
    neutral: true,
    inPlay,
    minute: inPlay ? "45" : "0",
    homeGoals: "0",
    awayGoals: "0",
    redHome: "0",
    redAway: "0",
  };
}

export function formatKickoff(kickoffUtc: string): string {
  const date = new Date(kickoffUtc);
  if (Number.isNaN(date.getTime())) return kickoffUtc;
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(date);
}
