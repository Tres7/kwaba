"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Minus, Plus } from "lucide-react";
import { useConfigPaiement } from "@/lib/paiement";
import { calculateServiceFee, cn } from "@/lib/utils";
import { useFormat } from "@/lib/format";

export type Partenaire = "particulier" | "fondateur" | "hotel";

const PARTENAIRES: Partenaire[] = ["particulier", "fondateur", "hotel"];
// Price grid, used while the API configuration has not been read (the server is authoritative)
const TAUX_PAR_DEFAUT = { particulier: 0.08, hotel: 0.12, fondateur: 0.05, voyageur: 0.06 };

/**
 * Estimate of a host's income: price per night they set, number of nights and partner type. The Kwa-Ba
 * commission is taken on the price of the nights; the traveller's service fees are added without reducing the
 * host's income. Same rounding to the franc as the server (apps/paiements/tarifs.py).
 *
 * - "Become a host" page: the visitor chooses their partner type and types a price;
 * - listing form: `partenaire` (set by the team) and `prix` (form field) are imposed.
 */
export default function EstimateurRevenus({ partenaire: partenaireImpose, prix: prixImpose, className }: {
  partenaire?: Partenaire;
  prix?: number;
  className?: string;
}) {
  const { formatFcfa } = useFormat();
  const t = useTranslations("estimateur");
  const { data: config } = useConfigPaiement();
  const [partenaireChoisi, setPartenaire] = useState<Partenaire>("particulier");
  const [prixSaisi, setPrix] = useState("25000");
  const [nuits, setNuits] = useState(1);

  const partenaire = partenaireImpose ?? partenaireChoisi;
  const prix = Math.max(0, Math.round(prixImpose ?? Number(prixSaisi))) || 0;
  const tauxCommission = config?.commissions?.[partenaire] ?? TAUX_PAR_DEFAUT[partenaire];
  const tauxVoyageur = config?.frais_voyageur ?? TAUX_PAR_DEFAUT.voyageur;

  const sousTotal = prix * nuits;
  const commission = calculateServiceFee(sousTotal, tauxCommission);
  const revenu = sousTotal - commission;
  const fraisVoyageur = calculateServiceFee(sousTotal, tauxVoyageur);
  const pourcent = (taux: number) => `${Math.round(taux * 100)} %`;

  const lignes: { libelle: string; valeur: string; fort?: boolean }[] = [
    { libelle: t("prixNuit"), valeur: formatFcfa(prix) },
    { libelle: t("commissionNuit", { taux: pourcent(tauxCommission) }), valeur: `− ${formatFcfa(calculateServiceFee(prix, tauxCommission))}` },
    { libelle: t("revenuNuit"), valeur: formatFcfa(prix - calculateServiceFee(prix, tauxCommission)) },
    { libelle: t("brut", { nuits }), valeur: formatFcfa(sousTotal) },
    { libelle: t("commissionTotale"), valeur: `− ${formatFcfa(commission)}` },
    { libelle: t("revenuEstime"), valeur: formatFcfa(revenu), fort: true },
  ];

  const champ = "w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base sm:text-sm text-dark outline-none focus:ring-4 focus:ring-primary/10";
  return (
    <div className={cn("bg-white rounded-3xl p-5 md:p-6 border border-gray-100", className)}>
      {!partenaireImpose && (
        <fieldset>
          <legend className="text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("type")}</legend>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {PARTENAIRES.map((p) => (
              <button key={p} type="button" aria-pressed={partenaire === p} onClick={() => setPartenaire(p)}
                className={cn("rounded-2xl border px-4 py-3 text-left transition-colors",
                  partenaire === p ? "border-primary bg-primary/5" : "border-gray-200 hover:border-primary/40")}>
                <span className="block font-bold text-dark text-sm">{t(`types.${p}.titre`)}</span>
                <span className="block text-xs text-gray-500 mt-0.5">{t(`types.${p}.texte`, { taux: pourcent(config?.commissions?.[p] ?? TAUX_PAR_DEFAUT[p]) })}</span>
              </button>
            ))}
          </div>
        </fieldset>
      )}
      {partenaireImpose && (
        <p className="text-sm text-gray-600">{t("votreType", { type: t(`types.${partenaire}.titre`), taux: pourcent(tauxCommission) })}</p>
      )}

      <div className={cn("grid gap-4 mt-4", prixImpose === undefined ? "sm:grid-cols-2" : "")}>
        {prixImpose === undefined && (
          <label className="block">
            <span className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("votrePrix")}</span>
            <input type="number" min={1} step={500} inputMode="numeric" value={prixSaisi} onChange={(e) => setPrix(e.target.value)} className={champ} />
          </label>
        )}
        <div>
          <span className="block text-xs font-bold text-dark uppercase tracking-wide mb-2" id="estimateur-nuits">{t("nuits")}</span>
          <div className="flex items-center gap-3" role="group" aria-labelledby="estimateur-nuits">
            <button type="button" onClick={() => setNuits((n) => Math.max(1, n - 1))} aria-label={t("moins")} disabled={nuits <= 1}
              className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center text-dark disabled:opacity-40"><Minus size={16} /></button>
            <span className="min-w-8 text-center font-bold text-dark" aria-live="polite">{nuits}</span>
            <button type="button" onClick={() => setNuits((n) => Math.min(90, n + 1))} aria-label={t("plus")}
              className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center text-dark"><Plus size={16} /></button>
          </div>
        </div>
      </div>

      <dl className="mt-5 divide-y divide-gray-100 text-sm" aria-live="polite">
        {lignes.map((l) => (
          <div key={l.libelle} className={cn("flex justify-between gap-4 py-2", l.fort && "text-base")}>
            <dt className={l.fort ? "font-bold text-dark" : "text-gray-600"}>{l.libelle}</dt>
            <dd className={cn("whitespace-nowrap", l.fort ? "font-heading font-bold text-secondary" : "text-dark")}>{l.valeur}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-gray-500 leading-relaxed">
        {t("voyageur", { total: formatFcfa(sousTotal + fraisVoyageur), frais: formatFcfa(fraisVoyageur), taux: pourcent(tauxVoyageur) })}
      </p>
      <p className="mt-1 text-xs text-gray-400">{t("note")}</p>
    </div>
  );
}
