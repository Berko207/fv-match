import { NextResponse } from "next/server";

import { pickDefaultFixture } from "@/core/fixtures";
import { fetchFwcFixtures } from "@/core/polymarket";

export const revalidate = 60;

export async function GET() {
  try {
    const fixtures = await fetchFwcFixtures();
    const defaultFixture = pickDefaultFixture(fixtures);

    return NextResponse.json({
      fixtures,
      defaultSlug: defaultFixture?.slug ?? null,
      fetchedAt: new Date().toISOString(),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load fixtures";
    return NextResponse.json({ error: message, fixtures: [], defaultSlug: null }, { status: 502 });
  }
}
