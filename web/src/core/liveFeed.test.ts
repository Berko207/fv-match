import { describe, expect, it } from "vitest";

import {
  type EspnEvent,
  isFinal,
  isLive,
  liveMatchToState,
  orientedTo,
  parseScoreboardEvent,
} from "./liveFeed";

function makeEvent({
  state = "in",
  clock = 3780 as number | null,
  detail = "63'",
  homeScore = "1",
  awayScore = "0",
}: {
  state?: string;
  clock?: number | null;
  detail?: string;
  homeScore?: string;
  awayScore?: string;
} = {}): EspnEvent {
  return {
    id: "760459",
    name: "Congo DR at Colombia",
    competitions: [
      {
        status: {
          clock: clock ?? undefined,
          displayClock: detail,
          type: { state, name: "STATUS_SECOND_HALF", detail, shortDetail: detail },
        },
        competitors: [
          { homeAway: "home", score: homeScore, team: { id: "203", displayName: "Colombia" } },
          { homeAway: "away", score: awayScore, team: { id: "21204", displayName: "Congo DR" } },
        ],
      },
    ],
  };
}

describe("parseScoreboardEvent", () => {
  it("extracts score, minute, status, and team ids", () => {
    const match = parseScoreboardEvent(makeEvent());
    expect(match).not.toBeNull();
    expect(match?.home).toBe("Colombia");
    expect(match?.away).toBe("Congo DR");
    expect(match?.homeGoals).toBe(1);
    expect(match?.awayGoals).toBe(0);
    expect(match?.minute).toBe(63); // clock 3780s / 60
    expect(match?.statusState).toBe("in");
    expect(match?.homeTeamId).toBe("203");
    expect(match?.awayTeamId).toBe("21204");
  });

  it("derives minute from clock across states", () => {
    expect(parseScoreboardEvent(makeEvent({ clock: 2700, detail: "HT" }))?.minute).toBe(45);
    const ft = parseScoreboardEvent(makeEvent({ state: "post", clock: null, detail: "FT" }));
    expect(ft?.minute).toBe(90);
    expect(ft && isFinal(ft)).toBe(true);
    const pre = parseScoreboardEvent(makeEvent({ state: "pre", clock: null, detail: "Sat" }));
    expect(pre?.minute).toBe(0);
  });

  it("falls back to leading digits of the detail string", () => {
    const match = parseScoreboardEvent(makeEvent({ clock: null, detail: "63'" }));
    expect(match?.minute).toBe(63);
  });

  it("returns null when competitors are missing", () => {
    expect(parseScoreboardEvent({ id: "x", competitions: [{ competitors: [] }] })).toBeNull();
    expect(parseScoreboardEvent({ id: "x" })).toBeNull();
  });
});

describe("orientedTo", () => {
  it("keeps goals when names match in order (Congo DR ~ DR Congo)", () => {
    const m = orientedTo(parseScoreboardEvent(makeEvent())!, "Colombia", "DR Congo");
    expect(m).not.toBeNull();
    expect(m?.home).toBe("Colombia");
    expect(m?.away).toBe("DR Congo");
    expect([m?.homeGoals, m?.awayGoals]).toEqual([1, 0]);
    expect(m && isLive(m)).toBe(true);
  });

  it("swaps goals and ids when names are reversed", () => {
    const m = orientedTo(parseScoreboardEvent(makeEvent())!, "DR Congo", "Colombia");
    expect(m).not.toBeNull();
    expect(m?.home).toBe("DR Congo");
    expect([m?.homeGoals, m?.awayGoals]).toEqual([0, 1]);
    expect(m?.homeTeamId).toBe("21204");
    expect(m?.awayTeamId).toBe("203");
  });

  it("returns null for a different fixture", () => {
    expect(orientedTo(parseScoreboardEvent(makeEvent())!, "France", "Spain")).toBeNull();
  });
});

describe("liveMatchToState", () => {
  it("maps a snapshot onto the in-play model LiveState", () => {
    const state = liveMatchToState(
      parseScoreboardEvent(makeEvent({ homeScore: "2", awayScore: "1" }))!,
    );
    expect(state.minute).toBe(63);
    expect(state.homeGoals).toBe(2);
    expect(state.awayGoals).toBe(1);
    expect(state.matchLength).toBe(90);
  });
});
