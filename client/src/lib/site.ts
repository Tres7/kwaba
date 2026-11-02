import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { filtrerLiens, type Module, type ReglagesSite } from "@/lib/modules";

export { filtrerLiens, PAGES_MODULES, moduleDuChemin, type Module, type ReglagesSite } from "@/lib/modules";

/** Settings read from the API: changing them only needs an API restart, without a new site image. */
export function useReglagesSite() {
  return useQuery({
    queryKey: ["site", "reglages"],
    queryFn: async () => (await api.get<ReglagesSite>("/v1/site/")).data,
    staleTime: 5 * 60_000,
  });
}

export async function envoyerReclamation(reclamation: FormData) {
  await api.post("/v1/site/reclamation/", reclamation, { headers: { "Content-Type": "multipart/form-data" } });
}

/** Module displayed? False while the settings are not read: a hidden module never shows, not even for an instant. */
export function useModule(nom: Module): boolean {
  return useReglagesSite().data?.modules[nom] === true;
}

/** Links whose page does not belong to a hidden module. */
export function useLiensVisibles<T extends { href: string }>(liens: T[]): T[] {
  return filtrerLiens(liens, useReglagesSite().data?.modules);
}
