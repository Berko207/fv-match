import type { Metadata } from "next";

import { MarketsBrowser } from "@/components/MarketsBrowser";

export const metadata: Metadata = {
  title: "Markets · fv-match",
  description:
    "Browse open Polymarket sports markets and the Byreal Predict curated catalog side by side.",
};

export default function MarketsPage() {
  return <MarketsBrowser />;
}
