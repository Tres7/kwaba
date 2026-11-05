import { VILLES, sansAccents, type CodePays, type Ville } from "./quartiers";

/**
 * Destination pages, one per country, city and district: /tg, /tg/lome, /tg/lome/tokoin (then /bj/cotonou… once
 * Benin opens: one more country here and its cities in lib/quartiers.ts). The address segment is the name without
 * accents nor spaces: "Bè Kpota" → be-kpota.
 */
export const PAYS: readonly CodePays[] = ["tg"];

export function slugDe(nom: string): string {
  return sansAccents(nom).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

export function estPays(code: string): code is CodePays {
  return (PAYS as readonly string[]).includes(code);
}

export function villesDuPays(pays: CodePays): Ville[] {
  return VILLES.filter((v) => v.pays === pays);
}

export function villeParSlug(pays: string, slug: string): Ville | undefined {
  return VILLES.find((v) => v.pays === pays && slugDe(v.nom) === slug);
}

export function quartierParSlug(ville: Ville, slug: string): string | undefined {
  return ville.quartiers.find((q) => slugDe(q) === slug);
}

export const cheminPays = (pays: CodePays) => `/${pays}`;
export const cheminVille = (ville: Ville) => `/${ville.pays}/${slugDe(ville.nom)}`;
export const cheminQuartier = (ville: Ville, quartier: string) => `${cheminVille(ville)}/${slugDe(quartier)}`;

/** Words of a place name, without accents nor punctuation, between spaces: "Lom-Nava" and "lom nava" are equal. */
const mots = (texte: string) => ` ${slugDe(texte).replace(/-/g, " ")} `;

/** City of the list typed by a host, with or without accents ("Lome" is Lomé); undefined for another city. */
export function villeDuNom(nom: string): Ville | undefined {
  const cle = mots(nom);
  return VILLES.find((v) => mots(v.nom) === cle);
}

/**
 * District of the list named in a listing's address ("Tokoin Casablanca" → Tokoin). The longest name wins
 * ("Bè Kpota" before "Bè"), so that a listing belongs to one district page only.
 */
export function quartierDeAdresse(ville: Ville, adresse: string): string | undefined {
  const texte = mots(adresse);
  return [...ville.quartiers].sort((a, b) => b.length - a.length).find((q) => texte.includes(mots(q)));
}

/** Listings of a country, a city or a district, with the same rules as the pages (city typed without accents). */
export function logementsDu<T extends { city: string; location: string }>(
  logements: readonly T[], lieu: { pays: CodePays; ville?: Ville; quartier?: string },
): T[] {
  return logements.filter((h) => {
    const ville = villeDuNom(h.city);
    if (!ville || ville.pays !== lieu.pays) return false;
    if (lieu.ville && ville !== lieu.ville) return false;
    return !lieu.quartier || quartierDeAdresse(ville, h.location) === lieu.quartier;
  });
}
