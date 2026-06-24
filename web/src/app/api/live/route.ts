import { NextResponse } from "next/server";

import { DEFAULT_LEAGUE, findLiveMatch } from "@/core/liveFeed";
import { fetchSiblingMarkets } from "@/core/polymarket";

// Live data — never cache.
export const dynamic = "force-dynamic";
export const revalidate = 0;

/**
 * GET /api/live?slug=<event>&league=<espn>&home=<>&away=<>
 *
 * Stitches the two free feeds server-side (both lack browser CORS): Polymarket
 * cross-market odds via the event slug, and ESPN live match state. Returns the
 * sibling markets plus the current in-play snapshot so the client can run the
 * in-play model and edge sweep. DRY_RUN — read-only, no orders.
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const slug = searchParams.get("slug");
    const league = searchParams.get("league") ?? DEFAULT_LEAGUE;
    if (!slug) {
      return NextResponse.json({ error: "slug required" }, { status: 400 });
    }

    const siblingMarkets = await fetchSiblingMarkets(slug);
    if (!siblingMarkets) {
      return NextResponse.json({ error: "markets not found" }, { status: 404 });
    }

    const home = searchParams.get("home") ?? siblingMarkets.home;
    const away = searchParams.get("away") ?? siblingMarkets.away;
    const match = await findLiveMatch(home, away, league);

    const live = match
      ? {
          minute: match.minute,
          homeGoals: match.homeGoals,
          awayGoals: match.awayGoals,
          redCardsHome: match.redCardsHome,
          redCardsAway: match.redCardsAway,
          statusState: match.statusState,
          statusDetail: match.statusDetail,
          statusName: match.statusName,
          isLive: match.statusState === "in",
          isFinal: match.statusState === "post",
        }
      : null;

    return NextResponse.json({
      home,
      away,
      siblingMarkets,
      live,
      status: live ? "live" : "no_live_state",
      fetchedAt: new Date().toISOString(),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Live fetch failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
