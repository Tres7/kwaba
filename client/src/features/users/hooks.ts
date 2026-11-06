import { useQuery } from "@tanstack/react-query";
import { lireDroitsAdmin, lireMoi } from "./api";
import type { Me } from "@/types/api/models";

export const CLE_MOI = ["me"];

export function useMoi(enabled = true) {
  return useQuery({ queryKey: CLE_MOI, queryFn: lireMoi, enabled });
}

/** What the signed-in admin can do. Display only: the API checks every request on its own. */
export function useDroitsAdmin(enabled = true) {
  return useQuery({ queryKey: ["admin", "droits"], queryFn: lireDroitsAdmin, enabled });
}

/** Host, administrator or candidate: may open the host space and prepare listings (same rule as the API).
 *  Read from the profile, not the session: the role changes on the server when an agent validates a listing. */
export function accesEspaceHote(moi: Pick<Me, "role" | "candidature_hote">) {
  return moi.role === "hote" || moi.role === "admin" || moi.candidature_hote === "ouverte";
}
