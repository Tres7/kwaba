import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { langueDe, metadataPage } from "@/lib/seo";
import { donneesSite } from "@/lib/donnees-structurees";
import JsonLd from "@/components/seo/JsonLd";
import Accueil from "@/features/hebergements/Accueil";

type Params = { params: Promise<{ locale: string }> };

/** Title with what people search ("logements vérifiés à Lomé"); the slogan stays in the default title of the site. */
export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const locale = langueDe((await params).locale);
  const t = await getTranslations({ locale, namespace: "meta" });
  return metadataPage({ locale, chemin: "/", titre: t("titreAccueil"), description: t("description"), titreComplet: true });
}

/** Home page: metadata and structured data rendered by the server, interactive content in Accueil (client component). */
export default async function Page({ params }: Params) {
  const locale = langueDe((await params).locale);
  const t = await getTranslations({ locale, namespace: "meta" });
  return (
    <>
      <JsonLd donnees={donneesSite(locale, t("slogan"))} />
      <Accueil />
    </>
  );
}
