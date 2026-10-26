import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { filtrerLiens, type Module, type ReglagesSite } from "@/lib/modules";

export { filtrerLiens, PAGES_MODULES, moduleDuChemin, type Module, type ReglagesSite } from "@/lib/modules";

/** Réglages lus dans l'API : les changer ne demande qu'un redémarrage de l'API, sans nouvelle image du site. */
export function useReglagesSite() {
  return useQuery({
    queryKey: ["site", "reglages"],
    queryFn: async () => (await api.get<ReglagesSite>("/v1/site/")).data,
    staleTime: 5 * 60_000,
  });
}

/** Module affiché ? Faux tant que les réglages ne sont pas lus : un module masqué n'apparaît jamais, même un instant. */
export function useModule(nom: Module): boolean {
  return useReglagesSite().data?.modules[nom] === true;
}

/** Liens dont la page n'appartient pas à un module masqué. */
export function useLiensVisibles<T extends { href: string }>(liens: T[]): T[] {
  return filtrerLiens(liens, useReglagesSite().data?.modules);
}
