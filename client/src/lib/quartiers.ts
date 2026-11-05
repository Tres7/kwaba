/** Countries with listings, by ISO 3166-1 code in lower case: the first segment of the city pages (/tg/lome). */
export type CodePays = "tg";

export interface Ville {
  nom: string;
  pays: CodePays;
  quartiers: readonly string[];
}

/**
 * Cities offered to hosts, with some of their districts: suggestions only, not a full list (a host can type another
 * district). Names checked against OpenStreetMap and local sources (2026-11). Choosing a district in the destination
 * field searches this name in the city and address of the listings (city filter of the API).
 */
export const VILLES: readonly Ville[] = [
  {
    nom: "Lomé",
    pays: "tg",
    quartiers: [
      "Adakpamé", "Adidogomé", "Agbalépédogan", "Agoè", "Amoutivé", "Avédji", "Baguida", "Bè", "Bè Kpota", "Cacavéli",
      "Djidjolé", "Gbossimé", "Hanoukopé", "Hédzranawoé", "Kégué", "Kodjoviakopé", "Lomé 2", "Nyékonakpoè", "Tokoin",
      "Totsi",
    ],
  },
  {
    nom: "Kpalimé",
    pays: "tg",
    quartiers: [
      "Dzodzekondzi", "Fiakomé", "Hanyigba", "Kliguekodzi", "Kpeta", "Kpodzi", "Kusuntu", "Lom-Nava", "Nyivémé",
      "Samkodzi", "Tsivé", "Zomayi", "Zongo",
    ],
  },
  { nom: "Aného", pays: "tg", quartiers: ["Adjido", "Anéhogan", "Fantékomé", "Glidji", "Gninkpanou", "Sahouèkomè", "Tôgonmè", "Zébé", "Zongomè"] },
  { nom: "Atakpamé", pays: "tg", quartiers: ["Agbonou", "Agbonou-Gare", "Djama", "Gnagna", "Houdou", "Koeroma", "Lom-Nava", "Sada"] },
  {
    nom: "Sokodé",
    pays: "tg",
    quartiers: ["Barrière", "Didaouré", "Komah", "Kossobio", "Koulounde", "Kpalo-Kpalo", "Kpangalam", "Tchawanda", "Tchogbala", "Zongo"],
  },
  { nom: "Kara", pays: "tg", quartiers: ["Belle-Ville", "Chaminade", "Kara Sud", "Lama-Feing", "Tchaloudè", "Tchintchinda", "Tomdè", "Yèou"] },
];

export const sansAccents = (texte: string) => texte.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();

/** Districts of a city typed by hand ("lome" → those of Lomé); none for a city that is not in the list. */
export function quartiersDe(ville: string): readonly string[] {
  const cle = sansAccents(ville);
  return VILLES.find((v) => sansAccents(v.nom) === cle)?.quartiers ?? [];
}

/** Districts whose name contains the input, ignoring accents and case ("nyeko" → Nyékonakpoè, Lomé), Lomé first. */
export function quartiersCorrespondants(saisie: string): { nom: string; ville: string }[] {
  const s = sansAccents(saisie);
  if (!s) return [];
  return VILLES.flatMap((v) => v.quartiers.filter((q) => sansAccents(q).includes(s)).map((nom) => ({ nom, ville: v.nom })));
}
