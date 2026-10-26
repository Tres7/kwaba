"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Clock, CreditCard, Loader2, Lock, Smartphone, Wallet, XCircle } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { allerPayer, enEuros, minutesRestantes, useConfigPaiement } from "@/lib/paiement";
import { cn, FALLBACK_IMAGE, formatDate, formatFcfa, formatPrice } from "@/lib/utils";
import { MontantDebite } from "@/components/layout/Devise";
import type { Reservation } from "@/types/api/models";
import type { MoyenPaiement, StatutPaiementReservation } from "@/types/api/paiement";
import { useTranslations } from "next-intl";

const MOYENS: { id: MoyenPaiement; label: string; icon: typeof Smartphone }[] = [
  { id: "mobile_money", label: "mobileMoney", icon: Smartphone },
  { id: "carte", label: "carte", icon: CreditCard },
  { id: "paypal", label: "paypal", icon: Wallet },
];

// Beyond that, the server is no longer polled: the worker and the webhook take over
const ATTENTE_MAX_MS = 3 * 60 * 1000;

function PaiementContent() {
  const t = useTranslations("paiement");
  const tRes = useTranslations("reservation");
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: config } = useConfigPaiement();
  const [debut] = useState(() => Date.now());
  const [moyen, setMoyen] = useState<MoyenPaiement | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState(searchParams.get("erreur") || "");
  const annuleParVoyageur = searchParams.get("annule") === "1";

  const { data: reservation } = useQuery({
    queryKey: ["reservation", params.id],
    queryFn: async () => (await api.get<Reservation>(`/v1/reservations/${params.id}/`)).data,
    retry: false,
  });

  const { data: statut, isError } = useQuery({
    queryKey: ["paiement-statut", params.id],
    queryFn: async () => (await api.get<StatutPaiementReservation>(`/v1/paiements/reservations/${params.id}/statut/`)).data,
    refetchInterval: (q) => {
      const s = q.state.data;
      const enAttente = s?.reservation === "pending" && s.paiement === "en_attente" && !annuleParVoyageur;
      return enAttente && Date.now() - debut < ATTENTE_MAX_MS ? 3000 : false;
    },
    retry: false,
  });

  useEffect(() => {
    if (statut?.reservation === "confirmed") {
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      queryClient.invalidateQueries({ queryKey: ["reservation", params.id] });
      router.replace(`/reservation/confirmation/${params.id}`);
    }
  }, [statut?.reservation, params.id, router, queryClient]);

  const moyensDispo = MOYENS.filter((m) => config?.moyens.includes(m.id));
  const moyenChoisi = moyen ?? (reservation && moyensDispo.some((m) => m.id === reservation.payment_method) ? reservation.payment_method : moyensDispo[0]?.id);

  const payer = async () => {
    if (!moyenChoisi) return;
    setEnvoi(true);
    setErreur("");
    try {
      await allerPayer(params.id, moyenChoisi);
    } catch (err) {
      setErreur(apiErrorMessage(err, t("paiementNonDemarre")));
      setEnvoi(false);
    }
  };

  if (isError) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
        <Link href="/profil/reservations" className="text-primary font-bold hover:underline">{t("voirMesReservations")}</Link>
      </div>
    );
  }

  const minutes = minutesRestantes(statut?.expire_le ?? null);
  const enAttente = statut?.reservation === "pending" && statut.paiement === "en_attente" && !annuleParVoyageur;
  const attenteLongue = enAttente && Date.now() - debut >= ATTENTE_MAX_MS;
  const aPayer = statut?.reservation === "pending" && !enAttente;
  const total = reservation?.montants.total ?? 0;

  return (
    <div className="bg-light min-h-[70vh]">
      <div className="max-w-xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
        <div className="bg-white rounded-3xl shadow-card border border-gray-100 p-6 sm:p-8" aria-live="polite">
          {!statut || statut.reservation === "confirmed" ? (
            <Etat icone={<Loader2 size={32} className="animate-spin text-primary" />} titre={t("verification")} />
          ) : statut.reservation === "cancelled" ? (
            <Etat
              icone={<XCircle size={32} className="text-red-600" />}
              titre={statut.annule_par === "expiration" ? t("delaiDepasse") : t("annulee")}
              texte={statut.annule_par === "expiration"
                ? t("delaiDepasseTexte")
                : t("annuleeTexte")}
            >
              {reservation && (
                <Link href={`/hebergements/${reservation.hebergement}`} className="inline-block mt-6 bg-primary text-white font-bold px-6 py-3 rounded-xl">
                  {t("reserverANouveau")}
                </Link>
              )}
            </Etat>
          ) : enAttente && !attenteLongue ? (
            <Etat
              icone={<Loader2 size={32} className="animate-spin text-primary" />}
              titre={t("attente")}
              texte={t("attenteTexte")}
            />
          ) : attenteLongue ? (
            <Etat
              icone={<Clock size={32} className="text-amber-600" />}
              titre={t("attenteLongue")}
              texte={t("attenteLongueTexte")}
            >
              <Link href="/profil/reservations" className="inline-block mt-6 bg-primary text-white font-bold px-6 py-3 rounded-xl">{t("mesReservations")}</Link>
            </Etat>
          ) : null}

          {aPayer && (
            <>
              <div className="text-center">
                <div className="w-16 h-16 mx-auto rounded-full bg-amber-50 flex items-center justify-center mb-4">
                  <AlertCircle size={30} className="text-amber-600" />
                </div>
                <h1 className="font-heading font-bold text-dark text-2xl">
                  {statut.paiement === "echoue" ? t("echoue") : annuleParVoyageur || statut.paiement === "annule" ? t("paiementAnnule") : t("enAttente")}
                </h1>
                <p className="text-gray-600 text-sm mt-2">
                  {t("aucunDebit")}{" "}
                  {minutes !== null && minutes > 0 && t.rich("datesBloquees", { minutes, strong: (x) => <strong>{x}</strong> })}
                </p>
              </div>

              {reservation && (
                <div className="flex gap-4 items-center mt-6 p-4 rounded-2xl bg-gray-50">
                  <img src={reservation.hebergement_detail.image_url || FALLBACK_IMAGE} alt="" className="w-16 h-16 rounded-xl object-cover flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="font-bold text-dark text-sm truncate">{reservation.hebergement_detail.name}</p>
                    <p className="text-xs text-gray-600">{formatDate(reservation.check_in)} → {formatDate(reservation.check_out)}</p>
                  </div>
                  <div className="text-right"><p className="font-heading font-bold text-dark whitespace-nowrap">{formatPrice(total)}</p><MontantDebite montant={total} /></div>
                </div>
              )}

              <fieldset className="mt-6">
                <legend className="text-xs font-bold text-dark uppercase tracking-wide mb-3">{t("payerAvec")}</legend>
                <div className="grid grid-cols-3 gap-2">
                  {moyensDispo.map(({ id, label, icon: Icon }) => (
                    <button
                      key={id} type="button" aria-pressed={moyenChoisi === id} onClick={() => setMoyen(id)}
                      className={cn("flex flex-col items-center gap-1.5 rounded-2xl border p-3 text-xs font-bold transition-colors",
                        moyenChoisi === id ? "border-primary bg-primary/5 text-primary" : "border-gray-200 text-dark hover:border-primary/40")}
                    >
                      <Icon size={20} /> {tRes(`moyens.${label}`)}
                    </button>
                  ))}
                </div>
              </fieldset>

              {erreur && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3 mt-4">{erreur}</p>}

              <button onClick={payer} disabled={envoi || !moyenChoisi}
                className="w-full mt-6 bg-secondary hover:bg-secondary-600 text-white font-bold py-4 rounded-2xl shadow-md disabled:opacity-60">
                {envoi ? t("redirection") : tRes("payer", { montant: moyenChoisi === "paypal" && config ? enEuros(total, config.fcfa_par_euro) : formatFcfa(total) })}
              </button>
              <p className="flex items-center justify-center gap-1.5 text-xs text-gray-600 mt-3">
                <Lock size={12} /> {t("securisePar", { prestataire: moyenChoisi === "paypal" ? "PayPal" : "FedaPay" })}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Etat({ icone, titre, texte, children }: { icone: React.ReactNode; titre: string; texte?: string; children?: React.ReactNode }) {
  return (
    <div className="text-center py-4">
      <div className="w-16 h-16 mx-auto rounded-full bg-gray-50 flex items-center justify-center mb-4">{icone}</div>
      <h1 className="font-heading font-bold text-dark text-2xl">{titre}</h1>
      {texte && <p className="text-gray-600 text-sm mt-2 max-w-md mx-auto">{texte}</p>}
      {children}
    </div>
  );
}

export default function PaiementPage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] bg-light" />}>
      <PaiementContent />
    </Suspense>
  );
}
