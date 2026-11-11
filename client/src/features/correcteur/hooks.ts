import { useReducer, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useLocale } from "next-intl";
import { useDebounced } from "@/lib/useAdminList";
import { verifierTexte } from "./api";
import { cleFaute, corriger as corrigerTexte, fautesEnPlace, toutCorriger as toutCorrigerTexte } from "./texte";
import type { Faute } from "./types";

/** The text is checked once the user stops typing for this long (ms) */
const DELAI = 900;
const LONGUEUR_MIN = 3;
/** Checker unavailable: the field asks again after this long (ms). While the API pauses LanguageTool, it answers at once */
const PAUSE = 20_000;

// Mistakes the user chose to ignore: for the whole visit and in every field (a name ignored in the title stays
// ignored in the description)
const ignorees = new Set<string>();

/**
 * Mistakes of a text being typed. The previous answer stays displayed while the next one is awaited, without the
 * mistakes whose text has changed. When the checker answers that it is unavailable, this field stops asking for
 * 20 seconds.
 */
export function useCorrecteur(texte: string) {
  const locale = useLocale();
  const stable = useDebounced(texte, DELAI);
  const [indisponible, setIndisponible] = useState(false);
  // Mistakes moved by a correction, shown until the corrected text has been checked
  const [apresCorrection, setApresCorrection] = useState<{ texte: string; fautes: Faute[] } | null>(null);
  const [, rafraichir] = useReducer((n: number) => n + 1, 0);

  const requete = useQuery({
    queryKey: ["correcteur", locale, stable],
    queryFn: async ({ signal }) => {
      const resultat = await verifierTexte(stable, locale, signal);
      if (!resultat.disponible) {
        setIndisponible(true);
        setTimeout(() => setIndisponible(false), PAUSE);
      }
      return resultat;
    },
    enabled: !indisponible && stable.trim().length >= LONGUEUR_MIN,
    placeholderData: keepPreviousData,
    // An answer « unavailable » is asked again after the pause; a real answer never changes for the same text
    staleTime: (query) => (query.state.data?.disponible === false ? 0 : Infinity),
    gcTime: 10 * 60_000,
    // Network error, too many checks: the field works without them
    retry: false,
  });
  const aJour = stable === texte && !requete.isPlaceholderData && !!requete.data;
  const brutes = !aJour && apresCorrection?.texte === texte ? apresCorrection.fautes : (requete.data?.fautes ?? []);
  const fautes = texte.trim().length >= LONGUEUR_MIN ? fautesEnPlace(texte, brutes, ignorees) : [];

  return {
    disponible: !indisponible,
    fautes,
    /** Text with `remplacement` instead of `faute` */
    corriger(faute: Faute, remplacement: string): string {
      const resultat = corrigerTexte(texte, fautes, faute, remplacement);
      setApresCorrection(resultat);
      return resultat.texte;
    },
    /** Text with every mistake that has a correction replaced by the first one */
    toutCorriger(): string {
      const resultat = toutCorrigerTexte(texte, fautes);
      setApresCorrection(resultat);
      return resultat.texte;
    },
    ignorer(faute: Faute) {
      ignorees.add(cleFaute(faute));
      rafraichir();
    },
  };
}
