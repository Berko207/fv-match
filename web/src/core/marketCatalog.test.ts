import { describe, expect, it } from "vitest";

import {
  byrealCategory,
  groupMatchEvents,
  isByrealCurated,
  parseGammaEvent,
} from "./marketCatalog";

describe("isByrealCurated", () => {
  it("includes World Cup match slugs", () => {
    expect(isByrealCurated("fifwc-bra-arg-2026-07-12")).toBe(true);
  });

  it("includes MLB game slugs", () => {
    expect(isByrealCurated("mlb-nyy-bos-2026-06-25", "Yankees vs Red Sox")).toBe(true);
  });

  it("includes NBA finals and champion markets", () => {
    expect(isByrealCurated("2026-nba-champion", "2026 NBA Champion")).toBe(true);
    expect(isByrealCurated("nba-finals-thunder-vs-pacers", "NBA Finals")).toBe(true);
  });

  it("excludes unrelated politics markets", () => {
    expect(isByrealCurated("will-trump-win", "Will Trump win?")).toBe(false);
  });
});

describe("byrealCategory", () => {
  it("maps slug prefixes to launch categories", () => {
    expect(byrealCategory("fifwc-usa-mex-2026-06-20")).toBe("football");
    expect(byrealCategory("mlb-oak-sf-2026-06-25")).toBe("baseball");
    expect(byrealCategory("2026-nba-champion", "2026 NBA Champion")).toBe("basketball");
  });
});

describe("parseGammaEvent", () => {
  it("parses child markets with yes/no odds", () => {
    const event = parseGammaEvent(
      {
        id: "1",
        slug: "fifwc-test-abc-2026-06-01",
        title: "Team A vs. Team B",
        closed: false,
        liquidity: 12000,
        volume24hr: 3400,
        markets: [
          {
            id: "m1",
            question: "Will Team A win?",
            groupItemTitle: "Team A",
            outcomePrices: '["0.40","0.60"]',
            closed: false,
            liquidityClob: "5000",
            sportsMarketType: "moneyline",
            comboStatus: "enabled",
          },
        ],
      },
      "fifa-world-cup",
    );

    expect(event).not.toBeNull();
    expect(event?.marketCount).toBe(1);
    expect(event?.markets[0].yesOdds).toBe(2.5);
    expect(event?.markets[0].noOdds).toBeCloseTo(1.667, 2);
    expect(event?.markets[0].sportsMarketType).toBe("moneyline");
    expect(event?.markets[0].comboStatus).toBe("enabled");
    expect(event?.matchBaseSlug).toBe("fifwc-test-abc-2026-06-01");
    expect(event?.polymarketUrl).toContain("polymarket.com/event/");
    expect(event?.byrealUrl).toContain("byreal.io");
  });
});

describe("groupMatchEvents", () => {
  it("merges sibling fifwc events into one match", () => {
    const mk = (slug: string, label: string, count: number) => ({
      id: slug,
      slug,
      title: "Japan vs. Sweden",
      description: "",
      category: "fifa-world-cup",
      status: "live" as const,
      kickoffUtc: "2026-06-25T19:00:00.000Z",
      liquidity: 100,
      volume24h: 50,
      closed: false,
      marketCount: count,
      markets: [],
      polymarketUrl: `https://polymarket.com/event/${slug}`,
      byrealUrl: null,
      gameId: 1,
      matchBaseSlug: "fifwc-jpn-swe-2026-06-25",
      subEventLabel: label,
      liveState: {
        live: true,
        ended: false,
        score: "0-0",
        period: "2H",
        elapsed: "51",
        homeTeam: "Japan",
        awayTeam: "Sweden",
        homeAbbrev: "jpn",
        awayAbbrev: "swe",
      },
    });

    const matches = groupMatchEvents([
      mk("fifwc-jpn-swe-2026-06-25", "Match result", 3),
      mk("fifwc-jpn-swe-2026-06-25-more-markets", "More Markets", 42),
    ]);

    expect(matches).toHaveLength(1);
    expect(matches[0].marketCount).toBe(45);
    expect(matches[0].subEventCount).toBe(2);
    expect(matches[0].liveState?.score).toBe("0-0");
  });
});
