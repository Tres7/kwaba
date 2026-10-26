/** Modules masquables (interrupteurs MODULE_… de l'environnement de l'API, voir server/config/site.py). */
export type Module = "experiences" | "together" | "give" | "concierge" | "location_sans_chauffeur" | "paiements_non_ouverts";

export interface ReglagesSite {
  modules: Record<Module, boolean>;
  /** Vide tant que la valeur n'est pas connue : le site affiche alors « à compléter ». */
  mentions: { rccm: string; nif: string; commerce_electronique: string; ipdcp: string };
  contact_email: string;
}

/**
 * Pages de chaque module : un module masqué disparaît des menus, du pied de page et du plan du site, et ses
 * adresses renvoient vers l'accueil (middleware).
 */
export const PAGES_MODULES: Record<string, Module> = {
  "/decouvrir": "experiences",
  "/together": "together",
  "/give": "give",
  "/concierge": "concierge",
};

export function moduleDuChemin(chemin: string): Module | null {
  const page = Object.keys(PAGES_MODULES).find((p) => chemin === p || chemin.startsWith(`${p}/`));
  return page ? PAGES_MODULES[page] : null;
}

/** Liens dont la page n'appartient pas à un module masqué (modules inconnus : tous masqués). */
export function filtrerLiens<T extends { href: string }>(liens: T[], modules: ReglagesSite["modules"] | undefined): T[] {
  return liens.filter((l) => {
    const nom = moduleDuChemin(l.href.split("?")[0]);
    return !nom || modules?.[nom] === true;
  });
}
