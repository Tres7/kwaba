import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { langueDe } from "@/lib/seo";
import { metadataDestination, trouverDestination } from "@/features/destinations/destination";
import PageDestination from "@/features/destinations/PageDestination";

type Params = { params: Promise<{ locale: string; pays: string; ville: string; quartier: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { locale, ...lieu } = await params;
  const destination = trouverDestination(lieu);
  return destination ? metadataDestination(langueDe(locale), destination) : {};
}

/** Listings of a district (/tg/lome/tokoin), among those of lib/quartiers.ts. */
export default async function Page({ params }: Params) {
  const { locale, ...lieu } = await params;
  const destination = trouverDestination(lieu);
  if (!destination) notFound();
  return <PageDestination locale={langueDe(locale)} destination={destination} />;
}
