import { useQuery } from "@tanstack/react-query";
import { lireMaPiece, lireTableauAgent, listerMissions, listerPositions } from "./api";
import type { CompteursVerification } from "./compteurs";

export type { CompteursVerification };

/** What field agents check (see server/apps/terrain/types.py). */
export type TypeMission = "logement" | "piece" | "photos";

export const TYPES_MISSION: { code: TypeMission; libelle: string; court: string }[] = [
  { code: "logement", libelle: "Logements à visiter", court: "Logements" },
  { code: "piece", libelle: "Pièces d'identité", court: "Pièces d'identité" },
  { code: "photos", libelle: "Photos à contrôler", court: "Photos" },
];

export interface MissionEtat {
  id: string;
  statut: "en_cours" | "terminee" | "liberee";
  decision: "" | "validee" | "refusee";
  agent: { id: string; nom: string } | null;
  /** The mission is mine. */
  moi: boolean;
  prise_le: string;
  terminee_le: string | null;
}

/** A list row: to do, my missions, the team or the history. */
export interface MissionResume {
  type: TypeMission;
  type_libelle: string;
  cible: string;
  titre: string;
  sous_titre: string;
  ville: string;
  adresse?: string;
  date: string;
  photo?: string | null;
  etiquette?: string;
  mission: MissionEtat | null;
}

export interface TableauAgent {
  types: { type: TypeMission; libelle: string; libres: number; miennes: number; equipe: number }[];
  faites_ce_mois: number;
  admin: boolean;
}

export type VueMissions = "a_faire" | "miennes" | "equipe" | "historique";

export const urlMission = (type: string, cible: string) => `/agent/mission/${type}/${cible}`;

/** Home and menu badges, refreshed every minute. */
export function useTableauAgent(actif = true) {
  return useQuery({
    queryKey: ["agent", "tableau"],
    enabled: actif,
    queryFn: lireTableauAgent,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export const CLE_MA_PIECE = ["verification", "identite"];

/** The host's own identity document. */
export function useMaPiece<T>() {
  return useQuery({ queryKey: CLE_MA_PIECE, queryFn: () => lireMaPiece<T>() });
}

export function useMissions(vue: VueMissions, filtres: { type?: TypeMission | ""; q?: string; agent?: "moi" | "" } = {}) {
  const params = Object.fromEntries(Object.entries({ vue, ...filtres }).filter(([, v]) => v));
  return useQuery({
    queryKey: ["agent", "missions", params],
    queryFn: () => listerMissions(params),
  });
}

/** A verified listing in the agent space's "Positions" page. */
export interface AnnoncePosition {
  id: string;
  name: string;
  type_libelle: string;
  city: string;
  location: string;
  point_repere: string;
  /** Exact current point: the host's, or the one an agent measured */
  position: { lat: number; lng: number } | null;
  /** When an agent measured or corrected it; null while it is the host's point */
  position_relevee_le: string | null;
  hote: { nom: string; telephone: string | null } | null;
}

export const CLE_POSITIONS = ["agent", "positions"];

export function usePositions(q: string, toutes: boolean) {
  return useQuery({ queryKey: [...CLE_POSITIONS, q, toutes], queryFn: () => listerPositions({ q, toutes }) });
}
