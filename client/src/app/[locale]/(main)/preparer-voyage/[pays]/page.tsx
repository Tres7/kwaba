import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { langueDe, lireApi, metadataPage } from "@/lib/seo";
import type { ReglagesSite } from "@/lib/modules";
import { GuideVoyage, guide } from "@/features/guides";

type Params = { params: Promise<{ locale: string; pays: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { locale, pays } = await params;
  const g = guide(pays, langueDe(locale));
  if (!g) return {};
  return metadataPage({ locale: langueDe(locale), chemin: `/preparer-voyage/${pays}`, titre: g.titre, description: g.description });
}

/** "Prepare your trip" guide of a country (features/guides). */
export default async function Page({ params }: Params) {
  const { locale, pays } = await params;
  const g = guide(pays, langueDe(locale));
  if (!g) notFound();
  // The links to a hidden module are left out (settings read again every 5 minutes)
  const reglages = await lireApi<ReglagesSite>("/v1/site/", 300);
  return <GuideVoyage guide={g} modules={reglages?.modules} />;
}
