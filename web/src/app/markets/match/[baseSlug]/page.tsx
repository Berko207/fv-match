import type { Metadata } from "next";

import { MatchDetail } from "@/components/MatchDetail";

export const metadata: Metadata = {
  title: "Match · fv-match",
};

export default async function MatchPage({
  params,
}: {
  params: Promise<{ baseSlug: string }>;
}) {
  const { baseSlug } = await params;
  return <MatchDetail baseSlug={baseSlug} />;
}
