import type { DonneesAnnonce } from "../brouillons";

export const MIN_PHOTOS = 5;
export const MAX_TITRE = 60;
export const MIN_TITRE = 8;
export const MIN_DESCRIPTION = 30;
export const MAX_DESCRIPTION = 2000;

export type CleEtape = "bienvenue" | "phase-1" | "type" | "espace" | "adresse" | "position" | "capacite"
  | "phase-2" | "equipements" | "photos" | "titre" | "description" | "fin";

export interface Etape {
  cle: CleEtape;
  /** 0: welcome screen, before the first phase */
  phase: 0 | 1 | 2;
  visuel: string;
  /** Large visual and short text, nothing to fill in */
  intro?: boolean;
  /** Screens that need the whole height on a phone (map, photos) show no visual there */
  sansVisuelMobile?: boolean;
  /** Can the host go on? Screens without a rule can be skipped. */
  pret?: (d: DonneesAnnonce) => boolean;
  /** Fields the API checks: while it refuses one of them, the host corrects it here rather than at the very end */
  champs?: (keyof DonneesAnnonce)[];
}

const visuel = (nom: string) => `/hote/${nom}.webp`;
const rempli = (texte?: string | null) => !!texte?.trim();
const nombreLits = (d: DonneesAnnonce) => (d.lits_doubles ?? 0) + (d.lits_simples ?? 0) + (d.canapes_lits ?? 0);

/** The wizard, in order. The cover photo and the price come from the same draft fields as the listing form. */
export const ETAPES: Etape[] = [
  { cle: "bienvenue", phase: 0, visuel: visuel("bienvenue"), intro: true },
  { cle: "phase-1", phase: 1, visuel: visuel("phase-1"), intro: true },
  { cle: "type", phase: 1, visuel: visuel("type-maison"), pret: (d) => !!d.type },
  { cle: "espace", phase: 1, visuel: visuel("espace-entier"), pret: (d) => !!d.espace },
  { cle: "adresse", phase: 1, visuel: visuel("adresse"), champs: ["city", "location"],
    pret: (d) => rempli(d.city) && rempli(d.location) },
  { cle: "position", phase: 1, visuel: visuel("position"), sansVisuelMobile: true,
    pret: (d) => d.latitude != null && d.longitude != null },
  { cle: "capacite", phase: 1, visuel: visuel("capacite"),
    pret: (d) => (d.max_guests ?? 0) >= 1 && (d.surface_m2 ?? 0) >= 5 && nombreLits(d) > 0 },
  { cle: "phase-2", phase: 2, visuel: visuel("phase-2"), intro: true },
  { cle: "equipements", phase: 2, visuel: visuel("equipements") },
  { cle: "photos", phase: 2, visuel: visuel("photos"), sansVisuelMobile: true,
    pret: (d) => (d.images?.length ?? 0) >= MIN_PHOTOS },
  { cle: "titre", phase: 2, visuel: visuel("titre"), champs: ["name"],
    pret: (d) => (d.name?.trim().length ?? 0) >= MIN_TITRE && (d.name?.length ?? 0) <= MAX_TITRE },
  { cle: "description", phase: 2, visuel: visuel("description"), champs: ["description"],
    pret: (d) => (d.description?.trim().length ?? 0) >= MIN_DESCRIPTION && (d.description?.length ?? 0) <= MAX_DESCRIPTION },
  { cle: "fin", phase: 2, visuel: visuel("phase-3"), intro: true },
];

/**
 * The screen to show: the requested one, or the first unanswered screen before it. An address can be typed or
 * bookmarked, and a draft resumed: nobody lands past a question left empty.
 */
export function etapeAffichee(demandee: string | null | undefined, d: DonneesAnnonce): Etape {
  const cible = ETAPES.findIndex((e) => e.cle === demandee);
  const fin = cible === -1 ? 0 : cible;
  return ETAPES.slice(0, fin).find((e) => e.pret && !e.pret(d)) ?? ETAPES[fin];
}

/** Can the host leave this screen? Answered, and nothing the API would refuse. */
export function peutContinuer(etape: Etape, d: DonneesAnnonce, erreurs: Record<string, string[]>): boolean {
  return (!etape.pret || etape.pret(d)) && !etape.champs?.some((champ) => erreurs[champ]?.length);
}

/** Share of each of the three phases already done (0 to 1), for the progress bar. The third one comes with the form. */
export function progressionPhases(cle: CleEtape): [number, number, number] {
  const courante = ETAPES.findIndex((e) => e.cle === cle);
  const part = (phase: number) => {
    const etapes = ETAPES.filter((e) => e.phase === phase);
    return etapes.filter((e) => ETAPES.indexOf(e) < courante).length / etapes.length;
  };
  return [part(1), part(2), 0];
}
