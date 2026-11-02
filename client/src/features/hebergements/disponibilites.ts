import { useQuery } from "@tanstack/react-query";
import { addDays, isoDate } from "@/lib/utils";
import { lireDisponibilites } from "./api";

export interface PeriodeIndispo {
  debut: string;
  fin: string;
  // Details reserved for the host of the listing
  type?: "reservation" | "blocage";
  id?: string;
  motif?: string;
  voyageur?: string;
  reference?: string;
  /** Units booked, and the unit type concerned (null: the whole establishment) */
  nb_unites?: number;
  type_logement?: string | null;
}

/** Unavailable nights (YYYY-MM-DD) of a list of periods [debut, fin). */
export function nuitsIndisponibles(periodes: PeriodeIndispo[]): Set<string> {
  const nuits = new Set<string>();
  for (const p of periodes) {
    for (let d = p.debut; d < p.fin; d = addDays(d, 1)) nuits.add(d);
  }
  return nuits;
}

/** Calendar of a listing over `jours` days from today: the full nights of a unit type if given, otherwise the
 *  nights when no type of the establishment has a unit left. */
export function useDisponibilites(hebergementId: string | undefined, jours = 365, typeLogement?: string) {
  const debut = isoDate();
  const fin = addDays(debut, jours);
  return useQuery({
    queryKey: ["disponibilites", hebergementId, debut, jours, typeLogement ?? ""],
    queryFn: () => lireDisponibilites(hebergementId as string, { debut, fin, ...(typeLogement ? { type_logement: typeLogement } : {}) }),
    enabled: !!hebergementId,
    staleTime: 30_000,
  });
}
