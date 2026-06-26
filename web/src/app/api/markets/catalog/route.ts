import { NextResponse } from "next/server";

import { fetchMarketsCatalog } from "@/core/marketCatalog";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const catalog = await fetchMarketsCatalog();
    return NextResponse.json(catalog);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to load market catalog";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
