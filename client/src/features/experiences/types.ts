import type { CategorieExperience } from "@/types/api/admin";

export type { CategorieExperience };

/** Experience published on the Discover page (the client chooses the language; an empty English text falls back to French). */
export interface Experience {
  id: number;
  categorie: CategorieExperience;
  nom: string;
  nom_en: string;
  etiquette: string;
  etiquette_en: string;
  ville: string;
  pays: string;
  pays_en: string;
  description: string;
  description_en: string;
  /** FCFA, indicative; null: no price displayed. */
  prix: number | null;
  gratuit: boolean;
  image: string | null;
}
