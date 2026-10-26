/**
 * Lomé districts offered in the destination field. Choosing one searches this name in the city and address of
 * the listings (city filter of the API).
 */
export const QUARTIERS_LOME = [
  "Adakpamé", "Adidogomé", "Agbalépédogan", "Agoè", "Amoutivé", "Avédji", "Baguida", "Bè", "Bè Kpota", "Cacavéli",
  "Djidjolé", "Gbossimé", "Hanoukopé", "Hédzranawoé", "Kégué", "Kodjoviakopé", "Lomé 2", "Nyékonakpoè", "Tokoin",
  "Totsi",
];

const sansAccents = (texte: string) => texte.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

/** Districts whose name contains the input, ignoring accents and case ("nyeko" → Nyékonakpoè). */
export function quartiersCorrespondants(saisie: string): string[] {
  const s = sansAccents(saisie.trim());
  if (!s) return [];
  return QUARTIERS_LOME.filter((q) => sansAccents(q).includes(s));
}
