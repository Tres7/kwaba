import { useLocale } from "next-intl";

const NOMS_PAYS: Record<string, { fr: string; en: string }> = {
  TG: { fr: "Togo", en: "Togo" }, BJ: { fr: "Bénin", en: "Benin" }, BF: { fr: "Burkina Faso", en: "Burkina Faso" },
  NE: { fr: "Niger", en: "Niger" }, ML: { fr: "Mali", en: "Mali" },
};

const noms = (langue: "fr" | "en") =>
  Object.fromEntries(Object.entries(NOMS_PAYS).map(([code, nom]) => [code, nom[langue]])) as Record<string, string>;

const PAYS = { fr: noms("fr"), en: noms("en") };

/** Country names in the language of the page (pays[code]). */
export function useNomsPays() {
  return PAYS[useLocale() === "en" ? "en" : "fr"];
}
