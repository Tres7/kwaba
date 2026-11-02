/** Modules masquables (interrupteurs MODULE_… de l'environnement de l'API, voir server/config/site.py). */
export type Module = "experiences" | "together" | "give" | "concierge" | "location_sans_chauffeur" | "paiements_non_ouverts";

export interface ReglagesSite {
  modules: Record<Module, boolean>;
  /** Empty while the value is not known: the site then shows "to be completed". */
  mentions: { rccm: string; nif: string; commerce_electronique: string; ipdcp: string };
  /** Company not registered yet (SOCIETE_EN_FORMATION): "SAS en formation" on the site. */
  en_formation: boolean;
  contact_email: string;
  /** Google Analytics measurement ID. Empty: no measurement, so no cookie banner. */
  mesure_audience: string;
}

/**
 * Pages of each module: a hidden module disappears from the menus, the footer and the sitemap, and its
 * addresses redirect to the home page (middleware).
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

/** Links whose page does not belong to a hidden module (unknown modules: all hidden). */
export function filtrerLiens<T extends { href: string }>(liens: T[], modules: ReglagesSite["modules"] | undefined): T[] {
  return liens.filter((l) => {
    const nom = moduleDuChemin(l.href.split("?")[0]);
    return !nom || modules?.[nom] === true;
  });
}
