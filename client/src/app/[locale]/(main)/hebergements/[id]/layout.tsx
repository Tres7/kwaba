import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { langueDe, lireApi, metadataPage } from "@/lib/seo";
import { libelleType } from "@/lib/utils";
import type { Hebergement } from "@/types/api/models";

const LONGUEUR_DESCRIPTION = 155;

function resume(texte: string): string {
  const propre = texte.replace(/\s+/g, " ").trim();
  if (propre.length <= LONGUEUR_DESCRIPTION) return propre;
  return `${propre.slice(0, LONGUEUR_DESCRIPTION).replace(/\s+\S*$/, "")}…`;
}

/**
 * Listing page: title, description and photo of the listing, rendered by the server for Google and link previews
 * (WhatsApp, Facebook). The page itself stays a client component.
 */
export async function generateMetadata({ params }: { params: Promise<{ locale: string; id: string }> }): Promise<Metadata> {
  const { locale: brut, id } = await params;
  const locale = langueDe(brut);
  const t = await getTranslations({ locale, namespace: "meta.pages" });
  const chemin = `/hebergements/${id}`;

  const h = await lireApi<Hebergement>(`/v1/hebergements/${encodeURIComponent(id)}/`);
  if (!h) {
    return metadataPage({ locale, chemin, titre: t("logementIntrouvable.titre"), indexable: false });
  }

  const prix = Math.round(Number(h.price_per_night)).toLocaleString(locale === "en" ? "en-GB" : "fr-FR").replace(/ /g, " ");
  const accroche = t("logementDescription", { type: libelleType(h.type, locale), ville: h.city, voyageurs: h.max_guests, prix });
  return metadataPage({
    locale,
    chemin,
    titre: `${h.name} · ${libelleType(h.type, locale)} ${locale === "en" ? "in" : "à"} ${h.city}`,
    // The host's text when it is long enough (unique content for Google), otherwise a generated sentence
    description: (h.description ?? "").trim().length >= 60 ? resume(h.description) : accroche,
    image: h.image_url || null,
    // Listing hidden by the host: the page can still be viewed but must not appear in Google
    indexable: h.is_available,
  });
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
