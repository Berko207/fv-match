import { NextResponse } from "next/server";

import { fetchMatchSurface } from "@/core/gameSurface";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(
  _request: Request,
  context: { params: Promise<{ baseSlug: string }> },
) {
  try {
    const { baseSlug } = await context.params;
    if (!baseSlug) {
      return NextResponse.json({ error: "baseSlug required" }, { status: 400 });
    }

    const surface = await fetchMatchSurface(baseSlug);
    if (!surface) {
      return NextResponse.json({ error: "match not found" }, { status: 404 });
    }

    return NextResponse.json(surface);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Fetch failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
