import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { addDays, isoDate } from "@/lib/utils";

export interface PeriodeIndispo {
  debut: string;
  fin: string;
  // Details reserved for the host of the listing
  type?: "reservation" | "blocage";
  id?: string;
  motif?: string;
  voyageur?: string;
  reference?: string;
}

/** Unavailable nights (YYYY-MM-DD) of a list of periods [debut, fin). */
export function nuitsIndisponibles(periodes: PeriodeIndispo[]): Set<string> {
  const nuits = new Set<string>();
  for (const p of periodes) {
    for (let d = p.debut; d < p.fin; d = addDays(d, 1)) nuits.add(d);
  }
  return nuits;
}

/** Calendar of a listing over `jours` days from today. */
export function useDisponibilites(hebergementId: string | undefined, jours = 365) {
  const debut = isoDate();
  const fin = addDays(debut, jours);
  return useQuery({
    queryKey: ["disponibilites", hebergementId, debut, jours],
    queryFn: async () =>
      (await api.get<{ periodes: PeriodeIndispo[] }>(`/v1/hebergements/${hebergementId}/disponibilites/`, { params: { debut, fin } })).data.periodes,
    enabled: !!hebergementId,
    staleTime: 30_000,
  });
}
