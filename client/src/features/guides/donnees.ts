import togoEn from "./togo.en";
import togoFr from "./togo.fr";
import type { GuidePays } from "./types";

/** The countries with a "Prepare your trip" guide, in each language. A new country: its two files and one line here. */
const GUIDES: Record<string, { fr: GuidePays; en: GuidePays }> = {
  togo: { fr: togoFr, en: togoEn },
};

export const PAYS_GUIDES = Object.keys(GUIDES);

export function guide(pays: string, langue: "fr" | "en"): GuidePays | null {
  return GUIDES[pays]?.[langue] ?? null;
}
