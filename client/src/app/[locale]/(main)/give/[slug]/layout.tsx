import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { langueDe, lireApi, metadataPage } from "@/lib/seo";
import type { Organisation } from "@/features/give";

/** Page of a Give organisation: name, presentation and image rendered by the server. */
export async function generateMetadata({ params }: { params: Promise<{ locale: string; slug: string }> }): Promise<Metadata> {
  const { locale: brut, slug } = await params;
  const locale = langueDe(brut);
  const t = await getTranslations({ locale, namespace: "meta.pages" });
  const chemin = `/give/${slug}`;

  const o = await lireApi<Organisation>(`/v1/give/organisations/${encodeURIComponent(slug)}/`);
  if (!o) return metadataPage({ locale, chemin, titre: "Kwa-Ba Give", indexable: false });

  return metadataPage({
    locale,
    chemin,
    titre: `${o.nom} · Kwa-Ba Give`,
    description: o.resume || t("organisationDescription", { nom: o.nom, ville: o.ville }),
    image: o.image || o.logo,
  });
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
