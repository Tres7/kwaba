"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CreditCard, Gift, Loader2, Lock, ShieldCheck, Smartphone, Wallet } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { apiErrorMessage } from "@/lib/api";
import { useFormat } from "@/lib/format";
import { cn, FALLBACK_IMAGE } from "@/lib/utils";
import { enEuros, useConfigPaiement, versPagePaiement } from "@/features/paiements";
import { MontantDebite } from "@/components/layout/Devise";
import type { MoyenPaiement } from "@/types/api/paiement";
import type { ApercuTiers } from "./types";

const MOYENS: { id: MoyenPaiement; label: string; icon: typeof Smartphone }[] = [
  { id: "mobile_money", label: "mobileMoney", icon: Smartphone },
  { id: "carte", label: "carte", icon: CreditCard },
  { id: "paypal", label: "paypal", icon: Wallet },
];

/**
 * Screen of the person who pays a stay in the traveller's place, reached by a secret link or from a Together trip.
 * `charger`: what they pay; `demarrer`: starts the payment and returns the provider's page.
 */
export default function PayerPourAutrui({ cle, charger, demarrer }: {
  cle: unknown[];
  charger: () => Promise<ApercuTiers>;
  demarrer: (moyen: MoyenPaiement) => Promise<string>;
}) {
  const t = useTranslations("paiementTiers");
  const tRes = useTranslations("reservation");
  const { formatDate, formatFcfa, formatPrice } = useFormat();
  const { data: config } = useConfigPaiement();
  const { data: apercu, isError, error } = useQuery({ queryKey: cle, queryFn: charger, retry: false });
  const [moyen, setMoyen] = useState<MoyenPaiement | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  const moyensDispo = MOYENS.filter((m) => config?.moyens.includes(m.id));
  const moyenChoisi = moyen ?? moyensDispo[0]?.id;

  const payer = async () => {
    if (!moyenChoisi) return;
    setEnvoi(true);
    setErreur("");
    try {
      versPagePaiement(await demarrer(moyenChoisi));
    } catch (err) {
      setErreur(apiErrorMessage(err, t("paiementNonDemarre")));
      setEnvoi(false);
    }
  };

  return (
    <div className="bg-light min-h-[70vh]">
      <div className="max-w-xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
        <div className="bg-surface rounded-3xl shadow-card border border-gray-100 p-6 sm:p-8" aria-live="polite">
          {isError ? (
            <div className="text-center py-4">
              <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
              <p className="text-sm text-gray-600 mt-2">{apiErrorMessage(error, t("introuvableTexte"))}</p>
              <Link href="/" className="inline-block mt-6 text-brand font-bold hover:underline">{t("accueil")}</Link>
            </div>
          ) : !apercu ? (
            <div className="flex justify-center py-10"><Loader2 size={32} className="animate-spin text-brand" /></div>
          ) : (
            <>
              <div className="text-center">
                <div className="w-16 h-16 mx-auto rounded-full bg-secondary/10 flex items-center justify-center mb-4">
                  <Gift size={30} className="text-secondary" />
                </div>
                <h1 className="font-heading font-bold text-dark text-2xl">{t("titre", { voyageur: apercu.voyageur })}</h1>
                <p className="text-gray-600 text-sm mt-2">{t("sousTitre", { voyageur: apercu.voyageur })}</p>
              </div>

              <div className="flex gap-4 items-center mt-6 p-4 rounded-2xl bg-gray-50">
                <img src={apercu.hebergement.image_url || FALLBACK_IMAGE} alt="" className="w-16 h-16 rounded-xl object-cover shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="font-bold text-dark text-sm truncate">{apercu.hebergement.name}</p>
                  <p className="text-xs text-gray-600">{apercu.hebergement.city}</p>
                  <p className="text-xs text-gray-600">
                    {formatDate(apercu.check_in)} → {formatDate(apercu.check_out)} · {t("voyageurs", { nombre: apercu.voyageurs })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-heading font-bold text-dark whitespace-nowrap">{formatPrice(apercu.total)}</p>
                  <MontantDebite montant={apercu.total} />
                </div>
              </div>

              {!apercu.payable ? (
                <p role="alert" className="text-sm text-amber-900 bg-amber-50 rounded-xl p-4 mt-6">{apercu.motif}</p>
              ) : (
                <>
                  <fieldset className="mt-6">
                    <legend className="text-xs font-bold text-dark uppercase tracking-wide mb-3">{t("payerAvec")}</legend>
                    <div className="grid grid-cols-3 gap-2">
                      {moyensDispo.map(({ id, label, icon: Icon }) => (
                        <button
                          key={id} type="button" aria-pressed={moyenChoisi === id} onClick={() => setMoyen(id)}
                          className={cn("flex flex-col items-center gap-1.5 rounded-2xl border p-3 text-xs font-bold transition-colors",
                            moyenChoisi === id ? "border-primary bg-primary/5 text-brand" : "border-gray-200 text-dark hover:border-primary/40")}
                        >
                          <Icon size={20} /> {tRes(`moyens.${label}`)}
                        </button>
                      ))}
                    </div>
                  </fieldset>

                  {erreur && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3 mt-4">{erreur}</p>}

                  <button onClick={payer} disabled={envoi || !moyenChoisi}
                    className="w-full mt-6 bg-secondary hover:bg-secondary-600 text-white font-bold py-4 rounded-2xl shadow-md disabled:opacity-60">
                    {envoi ? t("redirection") : tRes("payer", {
                      montant: moyenChoisi === "paypal" && config ? enEuros(apercu.total, config.fcfa_par_euro) : formatFcfa(apercu.total),
                    })}
                  </button>
                  <p className="flex items-center justify-center gap-1.5 text-xs text-gray-600 mt-3">
                    <Lock size={12} /> {t("securisePar", { prestataire: moyenChoisi === "paypal" ? "PayPal" : "FedaPay" })}
                  </p>
                </>
              )}

              <ul className="mt-6 space-y-2 text-xs text-gray-600">
                <li className="flex gap-2"><ShieldCheck size={14} className="text-brand shrink-0 mt-0.5" />{t("garantieRemboursement")}</li>
                <li className="flex gap-2"><ShieldCheck size={14} className="text-brand shrink-0 mt-0.5" />{t("garantieRecu")}</li>
                <li className="flex gap-2"><ShieldCheck size={14} className="text-brand shrink-0 mt-0.5" />{t("garantieConfidentialite", { voyageur: apercu.voyageur })}</li>
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
