import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

/** What field agents check (see server/apps/terrain/types.py). */
export type TypeMission = "logement" | "piece";

export const TYPES_MISSION: { code: TypeMission; libelle: string; court: string }[] = [
  { code: "logement", libelle: "Logements à visiter", court: "Logements" },
  { code: "piece", libelle: "Pièces d'identité", court: "Pièces d'identité" },
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
    queryFn: async () => (await api.get<TableauAgent>("/v1/agent/tableau/")).data,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export function useMissions(vue: VueMissions, filtres: { type?: TypeMission | ""; q?: string; agent?: "moi" | "" } = {}) {
  const params = Object.fromEntries(Object.entries({ vue, ...filtres }).filter(([, v]) => v));
  return useQuery({
    queryKey: ["agent", "missions", params],
    queryFn: async () => (await api.get<{ results: MissionResume[]; count: number }>("/v1/agent/missions/", { params })).data,
  });
}
