import type { Hebergement } from "@/types/api/models";

/** Fields of the listing form, as sent to the API; incomplete in a draft. */
export type DonneesAnnonce = Partial<Pick<Hebergement,
  "name" | "type" | "city" | "location" | "point_repere" | "max_guests" | "description" | "image_url" | "images" | "legendes_photos"
  | "amenities"
  | "chambres" | "salles_de_bain" | "lits_doubles" | "lits_simples" | "canapes_lits"
  | "petit_dejeuner" | "petit_dejeuner_prix" | "arrivee_a_partir" | "depart_avant" | "politique_annulation">> & {
  latitude?: number | string | null;
  longitude?: number | string | null;
  price_per_night?: number | null;
  /** Statements of the host, kept with the listing; `attestation`: the information is true */
  declarations?: { cameras?: boolean; animaux?: boolean; travaux?: boolean; attestation?: boolean } | null;
};

export interface BrouillonAnnonce {
  id: string;
  donnees: DonneesAnnonce;
  /** Wizard: screen to resume from (assistant/etapes.ts) */
  etape: string;
  cree_le: string;
  modifie_le: string;
}

/** Id of an uploaded photo, read from its address: hebergements/<host>/<id>.jpg (see _photo_upload_path on the API). */
export function photoDepuisUrl(url: string): string | null {
  return url.match(/\/hebergements\/[^/]+\/([0-9a-f-]{36})\.jpg/)?.[1] ?? null;
}

/** What the API requires to accept a new listing (HebergementCreateSerializer): messages annonce.completude.<cle>. */
const CRITERES: [string, (d: DonneesAnnonce) => boolean][] = [
  ["titre", (d) => !!d.name?.trim()],
  ["ville", (d) => !!d.city?.trim()],
  ["prix", (d) => (d.price_per_night ?? 0) > 0],
  ["position", (d) => d.latitude != null && d.longitude != null],
  ["pointRepere", (d) => !!d.point_repere?.trim()],
  ["sallesDeBain", (d) => (d.salles_de_bain ?? 0) >= 1],
  ["lits", (d) => (d.lits_doubles ?? 0) + (d.lits_simples ?? 0) + (d.canapes_lits ?? 0) > 0],
  ["petitDejeuner", (d) => !!d.petit_dejeuner && (d.petit_dejeuner !== "option" || (d.petit_dejeuner_prix ?? 0) > 0)],
  ["photos", (d) => (d.images?.length ?? 0) > 0],
  ["legendes", (d) => (d.images?.length ?? 0) > 0 && (d.images ?? []).every((url) => !!d.legendes_photos?.[url])],
];

/** Share of the required information filled in (100: the listing can be submitted) and the keys still missing. */
export function completude(donnees: DonneesAnnonce): { pourcentage: number; manquants: string[] } {
  const manquants = CRITERES.filter(([, rempli]) => !rempli(donnees)).map(([cle]) => cle);
  return { pourcentage: Math.round((100 * (CRITERES.length - manquants.length)) / CRITERES.length), manquants };
}
