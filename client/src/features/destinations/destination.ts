import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import type { Langue } from "@/i18n/routing";
import {
  cheminPays, cheminQuartier, cheminVille, estPays, logementsDu, quartierParSlug, slugDe, villeDuNom, villeParSlug,
} from "@/lib/destinations";
import { prixNuitAffiche } from "@/lib/donnees-structurees";
import type { ReglagesSite } from "@/lib/modules";
import type { CodePays, Ville } from "@/lib/quartiers";
import { lireApi, metadataPage } from "@/lib/seo";
import { formats } from "@/lib/utils";
import type { Hebergement } from "@/types/api/models";
import type { Experience } from "@/features/experiences";

/** Country, city or district page (/tg, /tg/lome, /tg/lome/tokoin). */
export interface Destination {
  pays: CodePays;
  ville?: Ville;
  quartier?: string;
}

/** Destination of an address; null for an unknown country, city or district (page not found). */
export function trouverDestination({ pays, ville, quartier }: { pays: string; ville?: string; quartier?: string }): Destination | null {
  if (!estPays(pays)) return null;
  if (!ville) return { pays };
  const v = villeParSlug(pays, ville);
  if (!v) return null;
  if (!quartier) return { pays, ville: v };
  const q = quartierParSlug(v, quartier);
  return q ? { pays, ville: v, quartier: q } : null;
}

export function cheminDe({ pays, ville, quartier }: Destination): string {
  if (!ville) return cheminPays(pays);
  return quartier ? cheminQuartier(ville, quartier) : cheminVille(ville);
}

/** "Prepare your trip" guide of each country (features/guides). */
export const GUIDES: Partial<Record<CodePays, string>> = { tg: "/preparer-voyage/togo" };

/**
 * Published listings read on the server (at most 200: the list API is not paginated). The API out of reach is an
 * error, not an empty list: an empty page would be sent to Google with "noindex".
 */
export async function lireLogements(): Promise<Hebergement[]> {
  const reponse = await lireApi<{ results: Hebergement[] }>("/v1/hebergements/", 600);
  if (!reponse) throw new Error("Logements injoignables : API hors d'atteinte");
  return reponse.results;
}

/** Ideas of things to do in a city (Discover page), when the module is shown. */
export async function lireExperiences(ville: Ville, modules?: ReglagesSite["modules"]): Promise<Experience[]> {
  if (!modules?.experiences) return [];
  const experiences = await lireApi<Experience[]>("/v1/experiences/", 3600);
  return (experiences ?? []).filter((e) => villeDuNom(e.ville) === ville);
}

type Traductions = Awaited<ReturnType<typeof getTranslations<"destinations">>>;

/** Title and place of a destination: "Logements vérifiés à Lomé, Togo", "à Lomé, Togo". */
export function textesDestination(t: Traductions, { pays, ville, quartier }: Destination) {
  const nomPays = t(`pays.${pays}.nom`);
  const lieu = !ville ? t(`pays.${pays}.dans`)
    : quartier ? t("dansQuartier", { quartier, ville: ville.nom })
    : t("dansVille", { ville: ville.nom, pays: nomPays });
  const intro = !ville ? t(`pays.${pays}.intro`)
    : quartier ? t("introQuartier", { quartier, ville: ville.nom })
    : t(`villes.${slugDe(ville.nom)}`);
  return { nomPays, lieu, titre: t("titre", { lieu }), intro };
}

/**
 * Metadata of a destination page. It is indexed only once it shows a listing: an empty page would be a "soft 404"
 * for Google (the sitemap follows the same rule).
 */
export async function metadataDestination(locale: Langue, destination: Destination): Promise<Metadata> {
  const [t, tous] = await Promise.all([getTranslations({ locale, namespace: "destinations" }), lireLogements()]);
  const logements = logementsDu(tous, destination);
  const { lieu, titre } = textesDestination(t, destination);
  const prixMin = Math.min(...logements.map(prixNuitAffiche));
  return metadataPage({
    locale,
    chemin: cheminDe(destination),
    titre,
    description: logements.length
      ? t("description", { nombre: logements.length, lieu, prix: formats(locale).formatFcfa(prixMin) })
      : t("descriptionVide", { lieu }),
    image: logements.find((h) => h.image_url)?.image_url || null,
    indexable: logements.length > 0,
  });
}
