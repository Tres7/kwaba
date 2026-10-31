import type { Hebergement } from "@/types/api/models";

/** Fields of the listing form, as sent to the API; incomplete in a draft. */
export type DonneesAnnonce = Partial<Pick<Hebergement,
  "name" | "type" | "city" | "location" | "max_guests" | "description" | "image_url" | "images" | "amenities"
  | "surface_m2" | "chambres" | "salles_de_bain" | "lits_doubles" | "lits_simples" | "canapes_lits"
  | "petit_dejeuner" | "petit_dejeuner_prix" | "arrivee_a_partir" | "depart_avant" | "politique_annulation">> & {
  latitude?: number | string | null;
  longitude?: number | string | null;
  price_per_night?: number | null;
};

export interface BrouillonAnnonce {
  id: string;
  donnees: DonneesAnnonce;
  cree_le: string;
  modifie_le: string;
}

/** What the API requires to accept a new listing (HebergementCreateSerializer): messages annonce.completude.<cle>. */
const CRITERES: [string, (d: DonneesAnnonce) => boolean][] = [
  ["titre", (d) => !!d.name?.trim()],
  ["ville", (d) => !!d.city?.trim()],
  ["prix", (d) => (d.price_per_night ?? 0) > 0],
  ["position", (d) => d.latitude != null && d.longitude != null],
  ["surface", (d) => (d.surface_m2 ?? 0) > 0],
  ["lits", (d) => (d.lits_doubles ?? 0) + (d.lits_simples ?? 0) + (d.canapes_lits ?? 0) > 0],
  ["petitDejeuner", (d) => !!d.petit_dejeuner && (d.petit_dejeuner !== "option" || (d.petit_dejeuner_prix ?? 0) > 0)],
  ["photos", (d) => (d.images?.length ?? 0) > 0],
];

/** Share of the required information filled in (100: the listing can be submitted) and the keys still missing. */
export function completude(donnees: DonneesAnnonce): { pourcentage: number; manquants: string[] } {
  const manquants = CRITERES.filter(([, rempli]) => !rempli(donnees)).map(([cle]) => cle);
  return { pourcentage: Math.round((100 * (CRITERES.length - manquants.length)) / CRITERES.length), manquants };
}
