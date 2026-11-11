import type { Faute } from "./types";

/** Key of an ignored mistake: the same text reported by the same rule, wherever it is. */
export function cleFaute(faute: Pick<Faute, "extrait" | "regle">): string {
  return `${faute.regle}|${faute.extrait}`;
}

/**
 * Mistakes still in their place: the text may have changed since it was checked (typing goes on), so a mistake whose
 * text is no longer at its position is dropped until the next check. Sorted, without overlaps, ignored ones removed.
 */
export function fautesEnPlace(texte: string, fautes: readonly Faute[], ignorees: ReadonlySet<string>): Faute[] {
  const resultat: Faute[] = [];
  let fin = 0;
  for (const faute of [...fautes].sort((a, b) => a.debut - b.debut)) {
    if (faute.debut < fin || ignorees.has(cleFaute(faute))) continue;
    if (texte.slice(faute.debut, faute.debut + faute.longueur) !== faute.extrait) continue;
    resultat.push(faute);
    fin = faute.debut + faute.longueur;
  }
  return resultat;
}

/** Text with `remplacement` instead of the mistake; the mistakes after it are moved by the change of length. */
export function corriger(texte: string, fautes: readonly Faute[], faute: Faute, remplacement: string): { texte: string; fautes: Faute[] } {
  const ecart = remplacement.length - faute.longueur;
  return {
    texte: texte.slice(0, faute.debut) + remplacement + texte.slice(faute.debut + faute.longueur),
    fautes: fautes.filter((f) => f !== faute).map((f) => (f.debut > faute.debut ? { ...f, debut: f.debut + ecart } : f)),
  };
}

/**
 * Mistake that « Fix all » may correct without asking: a spelling mistake (its first correction is the most likely),
 * or a grammar mistake with a single correction. « Les chambre » → « La chambre » or « Les chambres »: the host chooses.
 */
export function sansChoix(faute: Faute): boolean {
  return faute.remplacements.length > 0 && (faute.type === "orthographe" || faute.remplacements.length === 1);
}

/** Every mistake corrected without asking (`sansChoix`) replaced by its first correction, from the end of the text so
 * positions stay right; the other mistakes are kept, moved. */
export function toutCorriger(texte: string, fautes: readonly Faute[]): { texte: string; fautes: Faute[] } {
  return [...fautes]
    .filter(sansChoix)
    .sort((a, b) => b.debut - a.debut)
    .reduce((resultat, f) => corriger(resultat.texte, resultat.fautes, f, f.remplacements[0]), { texte, fautes: [...fautes] });
}

export interface Morceau {
  texte: string;
  faute?: Faute;
}

/** Text cut into plain parts and mistakes (sorted and without overlaps), for the underlining layer. */
export function morceaux(texte: string, fautes: readonly Faute[]): Morceau[] {
  const resultat: Morceau[] = [];
  let position = 0;
  for (const faute of fautes) {
    if (faute.debut > position) resultat.push({ texte: texte.slice(position, faute.debut) });
    resultat.push({ texte: texte.slice(faute.debut, faute.debut + faute.longueur), faute });
    position = faute.debut + faute.longueur;
  }
  if (position < texte.length) resultat.push({ texte: texte.slice(position) });
  return resultat;
}

/** Mistake under the caret (the caret just before or just after it counts). */
export function fauteA(fautes: readonly Faute[], position: number | null): Faute | undefined {
  if (position == null) return undefined;
  return fautes.find((f) => position >= f.debut && position <= f.debut + f.longueur);
}
