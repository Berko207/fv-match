import { describe, expect, it } from "vitest";

import { classifyMarketsToTabs, extractMoneyline } from "./gameSurface";
import type { CatalogEvent, CatalogMarket } from "./marketCatalog";

function mkMarket(
  id: string,
  groupTitle: string,
  sportsMarketType: string,
  yes = 0.5,
): CatalogMarket {
  return {
    id,
    slug: id,
    question: groupTitle,
    groupTitle,
    yesPrice: yes,
    noPrice: 1 - yes,
    yesOdds: 1 / yes,
    noOdds: 1 / (1 - yes),
    liquidity: 1000,
    closed: false,
    sportsMarketType,
    comboStatus: "enabled",
  };
}

function mkEvent(slug: string, markets: CatalogMarket[]): CatalogEvent {
  return {
    id: slug,
    slug,
    title: "Japan vs. Sweden",
    description: "",
    category: "fifa-world-cup",
    status: "live",
    kickoffUtc: "2026-06-25T19:00:00.000Z",
    liquidity: 100,
    volume24h: 50,
    closed: false,
    marketCount: markets.length,
    markets,
    polymarketUrl: `https://polymarket.com/event/${slug}`,
    byrealUrl: null,
    gameId: 1,
    matchBaseSlug: "fifwc-jpn-swe-2026-06-25",
    subEventLabel: slug.includes("-") ? slug.split("-").slice(-2).join(" ") : "Match result",
    liveState: null,
  };
}

describe("classifyMarketsToTabs", () => {
  it("routes player props into goals, assists, and shots tabs", () => {
    const base = "fifwc-jpn-swe-2026-06-25";
    const subEvents = [
      mkEvent(base, [
        mkMarket("h", "Japan", "moneyline", 0.25),
        mkMarket("d", "Draw (Japan vs. Sweden)", "moneyline", 0.5),
        mkMarket("a", "Sweden", "moneyline", 0.25),
      ]),
      mkEvent(`${base}-player-props`, [
        mkMarket("g1", "Ayase Ueda 1+ Goals", "soccer_player_goals"),
        mkMarket("a1", "Alexander Isak 1+ Assists", "soccer_player_assists"),
        mkMarket("s1", "Ayase Ueda 2+ Shots", "soccer_player_shots"),
      ]),
      mkEvent(`${base}-total-corners`, [
        mkMarket("c1", "O/U 9.5 Corners", "soccer_match_corners"),
      ]),
    ];

    const tabs = classifyMarketsToTabs(subEvents, base);
    expect(tabs["game-lines"]).toHaveLength(3);
    expect(tabs.goals).toHaveLength(1);
    expect(tabs.assists).toHaveLength(1);
    expect(tabs.shots).toHaveLength(1);
    expect(tabs.corners).toHaveLength(1);
  });
});

describe("extractMoneyline", () => {
  it("pulls H/D/A from the main event", () => {
    const base = "fifwc-jpn-swe-2026-06-25";
    const subEvents = [
      mkEvent(base, [
        mkMarket("h", "Japan", "moneyline", 0.267),
        mkMarket("d", "Draw (Japan vs. Sweden)", "moneyline", 0.4995),
        mkMarket("a", "Sweden", "moneyline", 0.2285),
      ]),
    ];
    const ml = extractMoneyline(subEvents, "Japan", "Sweden");
    expect(ml.homePct).toBeCloseTo(26.7, 0);
    expect(ml.drawPct).toBeCloseTo(49.95, 0);
    expect(ml.awayPct).toBeCloseTo(22.85, 0);
  });
});
