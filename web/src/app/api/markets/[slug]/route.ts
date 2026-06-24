import { NextResponse } from "next/server";

import { fetchSiblingMarkets } from "@/core/polymarket";

export const revalidate = 60;

export async function GET(
  _request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  try {
    const { slug } = await context.params;
    if (!slug) {
      return NextResponse.json({ error: "slug required" }, { status: 400 });
    }

    const markets = await fetchSiblingMarkets(slug);
    if (!markets) {
      return NextResponse.json({ error: "markets not found" }, { status: 404 });
    }

    return NextResponse.json({ markets, fetchedAt: new Date().toISOString() });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Fetch failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
