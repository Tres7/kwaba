import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { langueDe } from "@/lib/seo";
import { metadataDestination, trouverDestination } from "@/features/destinations/destination";
import PageDestination from "@/features/destinations/PageDestination";

type Params = { params: Promise<{ locale: string; pays: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { locale, ...lieu } = await params;
  const destination = trouverDestination(lieu);
  return destination ? metadataDestination(langueDe(locale), destination) : {};
}

/** Listings of a country (/tg): its cities and their listings. Any other first segment is not found. */
export default async function Page({ params }: Params) {
  const { locale, ...lieu } = await params;
  const destination = trouverDestination(lieu);
  if (!destination) notFound();
  return <PageDestination locale={langueDe(locale)} destination={destination} />;
}
