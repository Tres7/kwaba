import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import JsonLd from "@/components/seo/JsonLd";
import { cheminPays, cheminQuartier, cheminVille, quartierDeAdresse, villeDuNom } from "@/lib/destinations";
import { donneesLogement, filAriane, prixNuitAffiche } from "@/lib/donnees-structurees";
import { langueDe, lireApi, metadataPage } from "@/lib/seo";
import { formats, libelleType } from "@/lib/utils";
import type { Langue } from "@/i18n/routing";
import type { Hebergement } from "@/types/api/models";

const LONGUEUR_DESCRIPTION = 155;

type Params = { params: Promise<{ locale: string; id: string }> };

function resume(texte: string): string {
  const propre = texte.replace(/\s+/g, " ").trim();
  if (propre.length <= LONGUEUR_DESCRIPTION) return propre;
  return `${propre.slice(0, LONGUEUR_DESCRIPTION).replace(/\s+\S*$/, "")}…`;
}

/** "Lomé" even when the host typed "Lome". */
const nomVille = (h: Hebergement) => villeDuNom(h.city)?.nom ?? h.city;

const lireLogement = (id: string) => lireApi<Hebergement>(`/v1/hebergements/${encodeURIComponent(id)}/`);

/** The host's text when it is long enough (unique content for Google), otherwise a generated sentence. */
async function description(h: Hebergement, locale: Langue): Promise<string> {
  if ((h.description ?? "").trim().length >= 60) return resume(h.description);
  const t = await getTranslations({ locale, namespace: "meta.pages" });
  // Price of a night as the page shows it first: service fee included
  const prix = formats(locale).formatFcfa(prixNuitAffiche(h)).replace(/\s*FCFA$/, "");
  return t("logementDescription", { type: libelleType(h.type, locale), ville: nomVille(h), voyageurs: h.max_guests, prix });
}

/**
 * Listing page: title, description and photo of the listing, rendered by the server for Google and link previews
 * (WhatsApp, Facebook). The page itself stays a client component.
 */
export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { locale: brut, id } = await params;
  const locale = langueDe(brut);
  const chemin = `/hebergements/${id}`;

  const h = await lireLogement(id);
  if (!h) {
    const t = await getTranslations({ locale, namespace: "meta.pages" });
    return metadataPage({ locale, chemin, titre: t("logementIntrouvable.titre"), indexable: false });
  }

  return metadataPage({
    locale,
    chemin,
    titre: `${h.name} · ${libelleType(h.type, locale)} ${locale === "en" ? "in" : "à"} ${nomVille(h)}`,
    description: await description(h, locale),
    image: h.image_url || null,
    // Listing hidden by the host: the page can still be viewed but must not appear in Google
    indexable: h.is_available,
  });
}

/**
 * Structured data of a public listing (schema.org LodgingBusiness, its price and its breadcrumb through the destination
 * pages). Same API read as the metadata: the request is made once.
 */
export default async function Layout({ children, params }: { children: React.ReactNode } & Params) {
  const { locale: brut, id } = await params;
  const locale = langueDe(brut);
  const h = await lireLogement(id);
  if (!h?.is_available) return children;

  const t = await getTranslations({ locale, namespace: "destinations" });
  const ville = villeDuNom(h.city);
  const quartier = ville && quartierDeAdresse(ville, h.location);
  const etapes = [
    { nom: t("accueil"), chemin: "/" },
    ...(ville ? [{ nom: t(`pays.${ville.pays}.nom`), chemin: cheminPays(ville.pays) }, { nom: ville.nom, chemin: cheminVille(ville) }] : []),
    ...(ville && quartier ? [{ nom: quartier, chemin: cheminQuartier(ville, quartier) }] : []),
    { nom: h.name, chemin: `/hebergements/${h.id}` },
  ];
  return (
    <>
      <JsonLd donnees={[donneesLogement(h, locale, await description(h, locale)), filAriane(locale, etapes)]} />
      {children}
    </>
  );
}
