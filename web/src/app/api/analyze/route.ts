import { NextResponse } from "next/server";

import { analyzeMatch } from "@/core/engine";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      home,
      away,
      homeOdds,
      drawOdds,
      awayOdds,
      neutral,
      eloHome,
      eloAway,
      liveState,
    } = body ?? {};

    if (!home || !away) {
      return NextResponse.json(
        { error: "home and away team names are required" },
        { status: 400 },
      );
    }

    const analysis = analyzeMatch({
      home: String(home),
      away: String(away),
      homeOdds: homeOdds != null ? Number(homeOdds) : null,
      drawOdds: drawOdds != null ? Number(drawOdds) : null,
      awayOdds: awayOdds != null ? Number(awayOdds) : null,
      neutral: neutral !== false,
      eloHome: eloHome != null ? Number(eloHome) : null,
      eloAway: eloAway != null ? Number(eloAway) : null,
      liveState: liveState ?? null,
    });

    return NextResponse.json(analysis);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Analysis failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
