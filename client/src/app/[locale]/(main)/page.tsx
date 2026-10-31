import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { langueDe, metadataPage } from "@/lib/seo";
import Accueil from "@/features/hebergements/Accueil";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const locale = langueDe((await params).locale);
  const t = await getTranslations({ locale, namespace: "meta" });
  return metadataPage({ locale, chemin: "/", titre: t("titre"), description: t("description"), titreComplet: true });
}

/** Home page: metadata rendered by the server, interactive content in Accueil (client component). */
export default function Page() {
  return <Accueil />;
}
