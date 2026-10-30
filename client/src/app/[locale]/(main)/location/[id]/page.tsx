"use client";

import { Suspense, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Calendar, Car, CheckCircle, Clock, Loader2, Mail, MapPin, Users, XCircle } from "lucide-react";
import { Link } from "@/i18n/navigation";
import api, { apiErrorMessage } from "@/lib/api";
import { minutesRestantes, payerLocation, useConfigPaiement } from "@/lib/paiement";
import { cn } from "@/lib/utils";
import CompteRemboursementDialog from "@/components/paiement/CompteRemboursementDialog";
import Documents from "@/components/documents/Documents";
import type { MoyenPaiement } from "@/types/api/paiement";
import type { Location, StatutLocation } from "@/types/api/location";
import { useFormat } from "@/lib/format";

const STATUTS: Record<StatutLocation, { className: string; icon: typeof Clock }> = {
  en_attente_paiement: { className: "bg-amber-100 text-amber-800", icon: Clock },
  confirmee: { className: "bg-blue-50 text-blue-800", icon: CheckCircle },
  partenaire_assigne: { className: "bg-green-100 text-green-800", icon: CheckCircle },
  terminee: { className: "bg-gray-100 text-dark", icon: CheckCircle },
  annulee: { className: "bg-red-100 text-red-700", icon: XCircle },
};

const ATTENTE_MAX_MS = 3 * 60 * 1000;

function LocationDetail() {
  const { dateVol, formatPrice } = useFormat();
  const t = useTranslations("location");
  const td = useTranslations("location.detail");
  const tR = useTranslations("mesReservations");
  const tP = useTranslations("paiement");
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: config } = useConfigPaiement();
  const [debutPage] = useState(() => Date.now());
  const [envoi, setEnvoi] = useState(false);
  const [annulation, setAnnulation] = useState(false);
  const [aRembourser, setARembourser] = useState<number | null>(null);
  const annuleParVoyageur = searchParams.get("annule") === "1";

  const { data: l, isError, refetch } = useQuery({
    queryKey: ["location", params.id],
    queryFn: async () => (await api.get<Location>(`/v1/locations/${params.id}/`)).data,
    refetchInterval: (q) => {
      const d = q.state.data;
      const attente = d?.statut === "en_attente_paiement" && d.paiement === "en_attente" && !annuleParVoyageur;
      return attente && Date.now() - debutPage < ATTENTE_MAX_MS ? 3000 : false;
    },
    retry: false,
  });

  if (isError) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="font-heading font-bold text-xl text-dark">{td("introuvable")}</p>
        <Link href="/location" className="text-primary font-bold hover:underline">{t("mesLocations")}</Link>
      </div>
    );
  }
  if (!l) return <div className="max-w-3xl mx-auto px-4 py-10"><div className="h-96 skeleton rounded-3xl" /></div>;

  const statut = STATUTS[l.statut];
  const enAttente = l.statut === "en_attente_paiement" && l.paiement === "en_attente" && !annuleParVoyageur && Date.now() - debutPage < ATTENTE_MAX_MS;
  const aPayer = l.statut === "en_attente_paiement" && !enAttente;
  const moyens = (config?.moyens ?? []) as MoyenPaiement[];
  const minutes = minutesRestantes(l.expire_le);
  const v = l.vehicule_attribue;

  const payer = async (moyen: MoyenPaiement) => {
    setEnvoi(true);
    try {
      await payerLocation(l.id, moyen);
    } catch (err) {
      toast.error(apiErrorMessage(err, td("paiementNonDemarre")));
      setEnvoi(false);
    }
  };

  const annuler = async () => {
    const tardif = l.paiement === "reussi" && !l.annulation_gratuite;
    const question = tardif ? td("annulerPartiel", { montant: formatPrice(l.rembourse_si_annulation ?? 0) }) : td("annulerQuestion");
    if (!window.confirm(question)) return;
    setAnnulation(true);
    try {
      const res = await api.delete<{ rembourse: number; numero_requis: boolean }>(`/v1/locations/${l.id}/`);
      toast.success(res.data.rembourse > 0 ? td("annuleRembourse", { montant: formatPrice(res.data.rembourse) }) : td("annuleToast"));
      if (res.data.numero_requis) setARembourser(res.data.rembourse);
      queryClient.invalidateQueries({ queryKey: ["locations"] });
      refetch();
    } catch (err) {
      toast.error(apiErrorMessage(err, td("erreurAnnulation")));
    } finally {
      setAnnulation(false);
    }
  };

  const lieu = (nom: string, adresse: string) => (adresse ? `${nom}, ${adresse}` : nom);

  return (
    <div className="bg-light min-h-[70vh]">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-gray-600 font-mono">{l.reference}</p>
            <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl">{l.libelle} · {l.lieu_prise_detail.ville}</h1>
            <p className="text-sm text-gray-500">{t(`formules.${l.formule}`)}{l.categorie_detail?.exemple_modele ? ` · ${l.categorie_detail.exemple_modele}` : ""}</p>
          </div>
          <span className={cn("flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full", statut.className)}>
            <statut.icon size={13} /> {t(`statuts.${l.statut}`)}
          </span>
        </div>

        <div aria-live="polite">
          {enAttente && (
            <p className="flex items-center gap-3 bg-white rounded-2xl border border-gray-100 p-4 text-sm text-dark">
              <Loader2 size={18} className="animate-spin text-primary flex-shrink-0" /> {tP("verification")}
            </p>
          )}
          {l.statut === "confirmee" && <p className="bg-blue-50 text-blue-900 rounded-2xl p-4 text-sm">{td("recu")}</p>}
          {l.statut === "annulee" && l.annulee_par === "expiration" && (
            <p className="bg-red-50 text-red-800 rounded-2xl p-4 text-sm">
              {td("expire")} <Link href="/location" className="font-bold underline">{td("nouvelle")}</Link>
            </p>
          )}
        </div>

        {v && (
          <section className="bg-white rounded-3xl border-2 border-secondary/30 p-5 sm:p-6">
            <h2 className="font-heading font-bold text-dark text-lg">{td("votreVehicule")}</h2>
            {v.vehicule && (
              <div className="flex items-center gap-4 mt-4">
                <div className="w-14 h-14 rounded-full bg-secondary/10 text-secondary flex items-center justify-center flex-shrink-0"><Car size={24} aria-hidden /></div>
                <p className="min-w-0 font-bold text-dark">{v.vehicule}{v.immatriculation && <> · <span className="font-mono font-normal text-gray-600">{v.immatriculation}</span></>}</p>
              </div>
            )}
            <p className="flex items-start gap-2 mt-4 text-sm text-gray-600">
              <Mail size={16} className="text-secondary flex-shrink-0 mt-0.5" aria-hidden /> {td("coordonneesParEmail")}
            </p>
          </section>
        )}

        <section className="bg-white rounded-3xl border border-gray-100 p-5 sm:p-6">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="flex gap-3"><Calendar size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{t("prise")}</dt><dd className="font-semibold text-dark">{dateVol(l.debut_locale)}</dd><dd className="text-gray-600">{lieu(l.lieu_prise_detail.nom, l.adresse_prise)}</dd></div></div>
            <div className="flex gap-3"><MapPin size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{t("retour")}</dt><dd className="font-semibold text-dark">{dateVol(l.fin_locale)}</dd><dd className="text-gray-600">{lieu(l.lieu_retour_detail.nom, l.adresse_retour)}</dd></div></div>
            <div className="flex gap-3"><Users size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{t("passagers")}</dt><dd className="font-semibold text-dark">{l.passagers}</dd></div></div>
            <div className="sm:col-span-2 bg-gray-50 rounded-xl px-4 py-3"><dt className="text-gray-600">{t("precisions")}</dt><dd className="text-dark whitespace-pre-line mt-1">{l.precisions}</dd></div>
          </dl>
          <div className="mt-5 pt-4 border-t border-gray-100 space-y-1 text-sm">
            {l.prix_jour > 0 && <div className="flex justify-between"><span className="text-gray-600">{t("devisJours", { nombre: l.jours, prix: formatPrice(l.prix_jour) })}</span><span>{formatPrice(l.prix_jour * l.jours)}</span></div>}
            {l.prix_chauffeur > 0 && <div className="flex justify-between"><span className="text-gray-600">{t("devisChauffeur", { nombre: l.jours })}</span><span>{formatPrice(l.prix_chauffeur)}</span></div>}
            {l.primes > 0 && <div className="flex justify-between"><span className="text-gray-600">{t("devisPrimes")}</span><span>{formatPrice(l.primes)}</span></div>}
            {l.frais_lieux > 0 && <div className="flex justify-between"><span className="text-gray-600">{t("frais")}</span><span>{formatPrice(l.frais_lieux)}</span></div>}
            {l.caution_etat && <div className="flex justify-between"><span className="text-gray-600">{t("cautionLigne")}</span><span>{formatPrice(l.caution)}</span></div>}
            <div className="flex justify-between pt-2"><span className="text-gray-600">{l.paiement === "reussi" ? td("prixPaye") : td("prix")}</span><span className="font-heading font-bold text-xl text-dark">{formatPrice(l.a_payer)}</span></div>
            {l.caution_etat ? (
              l.statut !== "annulee" && (
                <p className="text-xs text-gray-500">
                  {l.caution_etat.restituee
                    ? td("cautionRestituee", { montant: formatPrice(l.caution - l.caution_etat.retenue) })
                    : t("cautionEnLigne", { heures: l.caution_etat.restitution_heures })}
                  {l.caution_etat.retenue > 0 && <> {td("cautionRetenue", { montant: formatPrice(l.caution_etat.retenue), motif: l.caution_etat.motif })}</>}
                </p>
              )
            ) : l.caution > 0 && <p className="text-xs text-gray-500">{t("caution", { montant: formatPrice(l.caution) })}</p>}
          </div>
          {l.remboursement && (
            l.remboursement.statut === "attente_numero" ? (
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-amber-900 bg-amber-50 rounded-xl px-3 py-2 mt-4">
                <span>{tR.rich("remboursementNumero", { montant: formatPrice(l.remboursement.montant), strong: (x) => <strong>{x}</strong> })}</span>
                <button onClick={() => setARembourser(l.remboursement!.montant)} className="px-4 py-1.5 rounded-full bg-secondary text-white text-xs font-bold">{tR("indiquerNumero")}</button>
              </div>
            ) : (
              <p className="text-sm text-dark bg-green-50 rounded-xl px-3 py-2 mt-4">
                {tR.rich(l.remboursement.statut === "envoye" ? "remboursementEffectue" : "remboursementEnCours", { montant: formatPrice(l.remboursement.montant), strong: (x) => <strong>{x}</strong> })}
              </p>
            )
          )}
          {l.paiement === "reussi" && <Documents objet="location" id={l.id} className="mt-4 pt-4 border-t border-gray-100" />}
        </section>

        {aPayer && (
          <section className="bg-white rounded-3xl border border-amber-200 p-5 sm:p-6">
            <h2 className="font-heading font-bold text-dark text-lg">{annuleParVoyageur || l.paiement === "annule" ? tP("paiementAnnule") : l.paiement === "echoue" ? tP("echoue") : tP("enAttente")}</h2>
            <p className="text-sm text-gray-600 mt-1">{tP("aucunDebit")}{minutes !== null && minutes > 0 && ` (${minutes} min)`}</p>
            <div className="flex flex-wrap gap-2 mt-4">
              {moyens.map((m) => (
                <button key={m} disabled={envoi} onClick={() => payer(m)} className="px-5 py-2.5 rounded-full bg-secondary text-white text-sm font-bold disabled:opacity-60">
                  {td("payerPar", { moyen: m === "mobile_money" ? "Mobile Money" : m === "carte" ? td("carte") : "PayPal" })}
                </button>
              ))}
            </div>
          </section>
        )}

        {["en_attente_paiement", "confirmee", "partenaire_assigne"].includes(l.statut) && (
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-gray-600">
              {l.paiement === "reussi" && l.rembourse_si_annulation !== null
                ? l.annulation_gratuite ? td("annulationGratuite") : td("rembourseSiAnnulation", { montant: formatPrice(l.rembourse_si_annulation) })
                : ""}
            </p>
            <button onClick={annuler} disabled={annulation} className="px-5 py-2 rounded-full bg-red-50 text-red-700 font-semibold hover:bg-red-100 disabled:opacity-50">
              {annulation ? td("annulation") : td("annuler")}
            </button>
          </div>
        )}

        <p className="text-center text-sm">
          <Link href="/location" className="text-primary font-bold hover:underline">{t("mesLocations")}</Link>
        </p>
      </div>

      {aRembourser !== null && (
        <CompteRemboursementDialog
          endpoint={`/v1/locations/${l.id}/compte-remboursement/`}
          montant={aRembourser}
          onClose={() => setARembourser(null)}
          onDone={() => {
            setARembourser(null);
            refetch();
            toast.success(tR("numeroEnregistre"));
          }}
        />
      )}
    </div>
  );
}

export default function LocationDetailPage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] bg-light" />}>
      <LocationDetail />
    </Suspense>
  );
}
