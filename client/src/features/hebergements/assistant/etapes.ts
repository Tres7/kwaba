import {
  Banknote, Building2, Camera, ClipboardCheck, Coffee, FilePen, House, IdCard, Images, KeyRound, ListChecks,
  Map as Carte, MapPin, NotebookPen, ScrollText, ShieldCheck, Signpost, Smartphone, Users, Wallet, Wifi, type LucideIcon,
} from "lucide-react";
import type { DonneesAnnonce } from "../brouillons";

export const MIN_PHOTOS = 5;
export const MAX_TITRE = 60;
export const MIN_TITRE = 8;
export const MIN_DESCRIPTION = 30;
export const MAX_DESCRIPTION = 2000;

export type CleEtape = "bienvenue" | "phase-1" | "type" | "adresse" | "position" | "capacite"
  | "phase-2" | "equipements" | "photos" | "titre" | "description"
  | "phase-3" | "prix" | "regles" | "accueil" | "securite" | "telephone" | "identite" | "versement" | "contrat" | "recapitulatif";

/** What the API says the host has done (GET brouillons/<id>/conditions/): it decides, the wizard only shows it. */
export interface Conditions {
  photos: boolean;
  photos_du_compte: boolean;
  attestation: boolean;
  telephone: boolean;
  identite: "absente" | "soumise" | "verifiee" | "refusee";
  versement: boolean;
  preinscription: boolean;
  contrat_a_signer: boolean;
  bloquants: string[];
}

export interface Etape {
  cle: CleEtape;
  /** 0: welcome screen, before the first phase */
  phase: 0 | 1 | 2 | 3;
  picto: LucideIcon;
  /** Large pictogram and short text, nothing to fill in */
  intro?: boolean;
  /** Screens that need the whole height on a phone (map, photos) show no visual there */
  sansVisuelMobile?: boolean;
  /** Can the host go on, from their answers? Screens without a rule can be skipped. */
  pret?: (d: DonneesAnnonce) => boolean;
  /** Can the host go on, from what the API knows: phone, identity document, payout account */
  fait?: (c: Conditions) => boolean;
  /** Nothing to do on this screen for this host */
  sauter?: (c: Conditions) => boolean;
  /** Fields the API checks: while it refuses one of them, the host corrects it here rather than at the very end */
  champs?: (keyof DonneesAnnonce)[];
}

/** Pictogram of each phase: on its first screen and in the list of the welcome screen. */
export const PICTOS_PHASES = { 1: House, 2: Camera, 3: ClipboardCheck } as const;
const rempli = (texte?: string | null) => !!texte?.trim();
const nombreLits = (d: DonneesAnnonce) => (d.lits_doubles ?? 0) + (d.lits_simples ?? 0) + (d.canapes_lits ?? 0);

/** The wizard, in order. */
export const ETAPES: Etape[] = [
  { cle: "bienvenue", phase: 0, picto: KeyRound, intro: true },
  { cle: "phase-1", phase: 1, picto: PICTOS_PHASES[1], intro: true },
  { cle: "type", phase: 1, picto: Building2, pret: (d) => !!d.type },
  { cle: "adresse", phase: 1, picto: MapPin, champs: ["city", "location", "point_repere"],
    pret: (d) => rempli(d.city) && rempli(d.location) && rempli(d.point_repere) },
  { cle: "position", phase: 1, picto: Carte, sansVisuelMobile: true,
    pret: (d) => d.latitude != null && d.longitude != null },
  { cle: "capacite", phase: 1, picto: Users,
    champs: ["max_guests", "chambres", "salles_de_bain"],
    pret: (d) => (d.max_guests ?? 0) >= 1 && (d.max_guests ?? 0) <= 20 && d.chambres != null && (d.salles_de_bain ?? 0) >= 1
      && nombreLits(d) > 0 },
  { cle: "phase-2", phase: 2, picto: PICTOS_PHASES[2], intro: true },
  { cle: "equipements", phase: 2, picto: Wifi },
  { cle: "photos", phase: 2, picto: Images, sansVisuelMobile: true, champs: ["images", "legendes_photos"],
    pret: (d) => (d.images?.length ?? 0) >= MIN_PHOTOS && (d.images ?? []).every((url) => !!d.legendes_photos?.[url]) },
  { cle: "titre", phase: 2, picto: Signpost, champs: ["name"],
    pret: (d) => (d.name?.trim().length ?? 0) >= MIN_TITRE && (d.name?.length ?? 0) <= MAX_TITRE },
  { cle: "description", phase: 2, picto: NotebookPen, champs: ["description"],
    pret: (d) => (d.description?.trim().length ?? 0) >= MIN_DESCRIPTION && (d.description?.length ?? 0) <= MAX_DESCRIPTION },
  { cle: "phase-3", phase: 3, picto: PICTOS_PHASES[3], intro: true },
  { cle: "prix", phase: 3, picto: Banknote, champs: ["price_per_night"], pret: (d) => (d.price_per_night ?? 0) > 0 },
  { cle: "regles", phase: 3, picto: ScrollText },
  { cle: "accueil", phase: 3, picto: Coffee,
    pret: (d) => !!d.petit_dejeuner && (d.petit_dejeuner !== "option" || (d.petit_dejeuner_prix ?? 0) > 0) },
  { cle: "securite", phase: 3, picto: ShieldCheck, pret: (d) => d.declarations?.attestation === true },
  { cle: "telephone", phase: 3, picto: Smartphone, fait: (c) => c.telephone },
  { cle: "identite", phase: 3, picto: IdCard, fait: (c) => c.identite === "soumise" || c.identite === "verifiee" },
  { cle: "versement", phase: 3, picto: Wallet, fait: (c) => c.versement },
  { cle: "contrat", phase: 3, picto: FilePen, fait: (c) => c.preinscription,
    sauter: (c) => c.preinscription && !c.contrat_a_signer },
  { cle: "recapitulatif", phase: 3, picto: ListChecks, fait: (c) => c.bloquants.length === 0 },
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

/** The screen before or after this one, without those that do not concern this host. */
export function etapeVoisine(etape: Etape, sens: 1 | -1, c?: Conditions): Etape | undefined {
  let i = ETAPES.indexOf(etape) + sens;
  while (ETAPES[i] && c && ETAPES[i].sauter?.(c)) i += sens;
  return ETAPES[i];
}

/** Can the host leave this screen? Answered, done, and nothing the API would refuse. */
export function peutContinuer(etape: Etape, d: DonneesAnnonce, erreurs: Record<string, string[]>, c?: Conditions): boolean {
  if (etape.pret && !etape.pret(d)) return false;
  if (etape.fait && !(c && etape.fait(c))) return false;
  return !etape.champs?.some((champ) => erreurs[champ]?.length);
}

/** Share of each of the three phases already done (0 to 1), for the progress bar. */
export function progressionPhases(cle: CleEtape): [number, number, number] {
  const courante = ETAPES.findIndex((e) => e.cle === cle);
  const part = (phase: number) => {
    const etapes = ETAPES.filter((e) => e.phase === phase);
    return etapes.filter((e) => ETAPES.indexOf(e) < courante).length / etapes.length;
  };
  return [part(1), part(2), part(3)];
}
