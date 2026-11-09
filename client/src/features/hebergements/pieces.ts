/**
 * Room shown by a listing photo (legendes_photos on the API, serializers.PIECES): bedrooms and bathrooms are numbered
 * ("chambre_2"), a studio has a main room instead of bedrooms.
 */
const AVANT = ["salon", "cuisine", "salle_a_manger"] as const;
const APRES = ["toilettes", "terrasse", "balcon", "jardin", "piscine", "salle_de_sport", "exterieur", "entree", "vue", "parking", "autre"] as const;
const NUMEROTEE = /^(chambre|salle_de_bain)_(\d+)$/;
/** A hotel, an aparthotel or a guesthouse: its spaces (the rooms of each type get their photos in the host space). */
const ETABLISSEMENT = ["exterieur", "reception", "chambres", "salles_de_bain", "restaurant", "bar", "piscine", "salle_de_sport",
  "salle_de_reunion", "terrasse", "jardin", "vue", "parking", "autre"] as const;

const serie = (base: string, nombre: number) => Array.from({ length: nombre }, (_, i) => `${base}_${i + 1}`);

/** The rooms the host can choose, in the order of a visit, for this number of bedrooms and bathrooms. */
export function codesPieces(chambres?: number | null, sallesDeBain?: number | null, etablissement = false): string[] {
  if (etablissement) return [...ETABLISSEMENT];
  return [
    ...(chambres ? serie("chambre", chambres) : ["piece_principale"]),
    ...AVANT,
    ...serie("salle_de_bain", Math.max(1, sallesDeBain ?? 1)),
    ...APRES,
  ];
}

/** Label of a room with the "pieces" messages: t("chambre", { numero: 2 }) → "Chambre 2". */
export function libellePiece(code: string, t: (cle: string, valeurs?: Record<string, number>) => string): string {
  const numerotee = code.match(NUMEROTEE);
  return numerotee ? t(numerotee[1], { numero: Number(numerotee[2]) }) : t(code);
}

/** Photos grouped by room, in the order of a visit (photos without a room last, under ""). */
export function photosParPiece(photos: string[], legendes: Record<string, string> | null | undefined): [string, string[]][] {
  const groupes = new Map<string, string[]>();
  for (const url of photos) {
    const piece = legendes?.[url] ?? "";
    groupes.set(piece, [...(groupes.get(piece) ?? []), url]);
  }
  const ordre = [...codesPieces(50, 50), ...ETABLISSEMENT.filter((c) => !codesPieces(50, 50).includes(c))];
  const rang = (piece: string) => (piece ? (ordre.indexOf(piece) + 1 || ordre.length) : ordre.length + 1);
  return [...groupes.entries()].sort(([a], [b]) => rang(a) - rang(b));
}
