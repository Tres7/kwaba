import { lireApi } from "@/lib/seo";

/** The traveller's fee rates written in the terms of sale, as shown ("6 %", "3 %"). */
export interface TauxCgv {
  voyageur: string;
  reduits: string;
}

/** Rates set in the back-office (re-read every 5 minutes); the grid of 18 October 2026 if the API cannot be reached. */
export async function tauxCgv(locale: "fr" | "en"): Promise<TauxCgv> {
  const config = await lireApi<{ frais_voyageur: number; frais_reduits: number }>("/v1/paiements/config/", 300);
  const pourcent = (taux: number) => {
    const nombre = new Intl.NumberFormat(locale === "en" ? "en-GB" : "fr-FR", { maximumFractionDigits: 2 }).format(taux * 100);
    return locale === "en" ? `${nombre}%` : `${nombre} %`;
  };
  return { voyageur: pourcent(config?.frais_voyageur ?? 0.06), reduits: pourcent(config?.frais_reduits ?? 0.03) };
}
