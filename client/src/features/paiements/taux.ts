import { useLocale } from "next-intl";
import { useConfigPaiement } from "./paiement";

/** Grid of 18 October 2026: shown while the settings load. */
const PAR_DEFAUT = { voyageur: 0.06, reduits: 0.03, particulier: 0.08, hotel: 0.12, fondateur: 0.05 };
export type CleTaux = keyof typeof PAR_DEFAUT;

/** "6 %" in French, "6%" in English, with decimals when the team set some ("6,5 %"). */
export function formatPourcent(taux: number, langue: string): string {
  const nombre = new Intl.NumberFormat(langue === "en" ? "en-GB" : "fr-FR", { maximumFractionDigits: 2 }).format(taux * 100);
  return langue === "en" ? `${nombre}%` : `${nombre} %`;
}

/**
 * The rates set in the back-office (Tarifs): fees and commissions as numbers and as text. Every page that shows a rate
 * reads it here, so a change shows everywhere at once.
 */
export function useTaux() {
  const langue = useLocale();
  const { data } = useConfigPaiement();
  const taux: Record<CleTaux, number> = {
    voyageur: data?.frais_voyageur ?? PAR_DEFAUT.voyageur,
    reduits: data?.frais_reduits ?? PAR_DEFAUT.reduits,
    particulier: data?.commissions?.particulier ?? PAR_DEFAUT.particulier,
    hotel: data?.commissions?.hotel ?? PAR_DEFAUT.hotel,
    fondateur: data?.commissions?.fondateur ?? PAR_DEFAUT.fondateur,
  };
  const texte = Object.fromEntries(Object.entries(taux).map(([cle, valeur]) => [cle, formatPourcent(valeur, langue)])) as Record<CleTaux, string>;
  return { taux, texte, pourcent: (valeur: number) => formatPourcent(valeur, langue) };
}
