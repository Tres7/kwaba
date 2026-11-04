/**
 * "Prepare your trip" guide of a country: the same headings for every country (template), filled in French and in
 * English. Adding a country = one fr file and one en file, nothing else to build.
 */
export type IconeRubrique =
  | "passeport" | "sante" | "argent" | "avion" | "deplacements" | "telephone" | "climat" | "prise" | "logement"
  | "securite" | "usages";

/** Fixed headings, in this order, for every country. */
export const RUBRIQUES = [
  "formalites", "sante", "argent", "arriver", "deplacements", "telephone", "climat", "electricite", "loger", "securite",
  "usages",
] as const;
export type CleRubrique = (typeof RUBRIQUES)[number];

export interface Rubrique {
  titre: string;
  icone: IconeRubrique;
  /** One idea per line; **bold** for the word to remember */
  points: string[];
  /** Official pages that say the same thing: rules change, the traveller checks there */
  sources?: { libelle: string; url: string }[];
  /** Kwa-Ba service that answers the need (a hidden module's link is left out) */
  action?: { libelle: string; href: string };
}

export interface GuidePays {
  code: string;
  nom: string;
  titre: string;
  description: string;
  intro: string;
  /** Shown as is: "Mis à jour le 4 novembre 2026" */
  misAJour: string;
  avertissement: string;
  sommaire: string;
  sourcesTitre: string;
  rubriques: Record<CleRubrique, Rubrique>;
}
