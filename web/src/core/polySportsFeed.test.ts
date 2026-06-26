import { describe, expect, it } from "vitest";

import {
  formatSportUpdateLine,
  parsePolySportMessage,
} from "./polySportsFeed";

describe("parsePolySportMessage", () => {
  it("parses a soccer sport_result payload", () => {
    const update = parsePolySportMessage(
      JSON.stringify({
        gameId: 90086965,
        leagueAbbreviation: "fifwc",
        slug: "fifwc-jpn-swe-2026-06-25",
        homeTeam: "JPN",
        awayTeam: "SWE",
        status: "InProgress",
        score: "1-0",
        period: "2H",
        elapsed: "51",
        live: true,
        ended: false,
      }),
    );

    expect(update?.slug).toBe("fifwc-jpn-swe-2026-06-25");
    expect(update?.live).toBe(true);
    expect(update?.score).toBe("1-0");
  });

  it("ignores ping/pong heartbeats", () => {
    expect(parsePolySportMessage("ping")).toBeNull();
    expect(parsePolySportMessage("pong")).toBeNull();
  });
});

describe("formatSportUpdateLine", () => {
  it("formats a readable log line", () => {
    const line = formatSportUpdateLine({
      gameId: 1,
      leagueAbbreviation: "fifwc",
      slug: "fifwc-jpn-swe-2026-06-25",
      homeTeam: "JPN",
      awayTeam: "SWE",
      status: "InProgress",
      score: "1-0",
      period: "2H",
      elapsed: "51",
      live: true,
      ended: false,
      receivedAt: "2026-06-25T00:00:00.000Z",
    });
    expect(line).toContain("LIVE");
    expect(line).toContain("1-0");
  });
});
