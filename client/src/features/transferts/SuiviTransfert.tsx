"use client";

import { adresseCompteRemboursement, annulerTransfert, lireTransfert } from "./api";
import { clesTransferts } from "./hooks";
import { Suspense, useState } from "react";
import { Link } from "@/i18n/navigation";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Clock, Loader2, MapPin, MessageCircle, Phone, Plane, Users, Luggage, XCircle, Car } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { payerTransfert, minutesRestantes, useConfigPaiement } from "@/features/paiements";
import { cn } from "@/lib/utils";
import { CompteRemboursementDialog } from "@/features/paiements";
import { Documents } from "@/features/documents";
import type { MoyenPaiement } from "@/types/api/paiement";
import type { StatutTransfert } from "./types";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

const STATUTS: Record<StatutTransfert, { label: string; className: string; icon: typeof Clock }> = {
  en_attente_paiement: { label: "enAttente", className: "bg-amber-100 text-amber-800", icon: Clock },
  confirme: { label: "confirme", className: "bg-blue-50 text-blue-800", icon: CheckCircle },
  chauffeur_assigne: { label: "chauffeurAttribue", className: "bg-green-100 text-green-800", icon: CheckCircle },
  termine: { label: "effectue", className: "bg-gray-100 text-dark", icon: CheckCircle },
  annule: { label: "annule", className: "bg-red-100 text-red-700", icon: XCircle },
};

const ATTENTE_MAX_MS = 3 * 60 * 1000;

function TransfertDetail() {
  const { dateVol, formatPrice } = useFormat();
  const tr = useTranslations("transfertDetail");
  const tT = useTranslations("transfert");
  const tR = useTranslations("mesReservations");
  const tP = useTranslations("paiement");
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: config } = useConfigPaiement();
  const [debut] = useState(() => Date.now());
  const [envoi, setEnvoi] = useState(false);
  const [annulation, setAnnulation] = useState(false);
  const [aRembourser, setARembourser] = useState<number | null>(null);
  const annuleParVoyageur = searchParams.get("annule") === "1";

  const { data: t, isError, refetch } = useQuery({
    queryKey: ["transfert", params.id],
    queryFn: () => lireTransfert(params.id),
    refetchInterval: (q) => {
      const d = q.state.data;
      const attente = d?.statut === "en_attente_paiement" && d.paiement === "en_attente" && !annuleParVoyageur;
      return attente && Date.now() - debut < ATTENTE_MAX_MS ? 3000 : false;
    },
    retry: false,
  });

  if (isError) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="font-heading font-bold text-xl text-dark">{tr("introuvable")}</p>
        <Link href="/profil/transferts" className="text-primary font-bold hover:underline">{tr("mesTransferts")}</Link>
      </div>
    );
  }
  if (!t) return <div className="max-w-3xl mx-auto px-4 py-10"><div className="h-96 skeleton rounded-3xl" /></div>;

  const statut = STATUTS[t.statut];
  const enAttente = t.statut === "en_attente_paiement" && t.paiement === "en_attente" && !annuleParVoyageur && Date.now() - debut < ATTENTE_MAX_MS;
  const aPayer = t.statut === "en_attente_paiement" && !enAttente;
  const moyens = (config?.moyens ?? []) as MoyenPaiement[];
  const minutes = minutesRestantes(t.expire_le);

  const payer = async (moyen: MoyenPaiement) => {
    setEnvoi(true);
    try {
      await payerTransfert(t.id, moyen);
    } catch (err) {
      toast.error(apiErrorMessage(err, tr("paiementNonDemarre")));
      setEnvoi(false);
    }
  };

  const annuler = async () => {
    const question = t.paiement === "reussi" && !t.annulation_gratuite
      ? tr("annulerTardif")
      : tr("annulerQuestion");
    if (!window.confirm(question)) return;
    setAnnulation(true);
    try {
      const { rembourse, numero_requis } = await annulerTransfert(t.id);
      toast.success(rembourse > 0 ? tr("annuleRembourse", { montant: formatPrice(rembourse) }) : tr("annuleToast"));
      if (numero_requis) setARembourser(rembourse);
      queryClient.invalidateQueries({ queryKey: clesTransferts.tous });
      refetch();
    } catch (err) {
      toast.error(apiErrorMessage(err, tr("erreurAnnulation")));
    } finally {
      setAnnulation(false);
    }
  };

  return (
    <div className="bg-light min-h-[70vh]">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-gray-600 font-mono">{t.reference}</p>
            <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl">{tr("depuis", { ville: t.aeroport_detail.ville })}</h1>
          </div>
          <span className={cn("flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full", statut.className)}>
            <statut.icon size={13} /> {tr(`statuts.${statut.label}`)}
          </span>
        </div>

        <div aria-live="polite">
          {enAttente && (
            <p className="flex items-center gap-3 bg-white rounded-2xl border border-gray-100 p-4 text-sm text-dark">
              <Loader2 size={18} className="animate-spin text-primary flex-shrink-0" />
              {tr("attente")}
            </p>
          )}
          {t.statut === "confirme" && (
            <p className="bg-blue-50 text-blue-900 rounded-2xl p-4 text-sm">
              {tr("recu")}
            </p>
          )}
          {t.statut === "annule" && t.annule_par === "expiration" && (
            <p className="bg-red-50 text-red-800 rounded-2xl p-4 text-sm">
              {tr("expire")}{" "}
              <Link href="/transfert" className="font-bold underline">{tr("nouveau")}</Link>
            </p>
          )}
        </div>

        {t.chauffeur && (
          <section className="bg-white rounded-3xl border-2 border-secondary/30 p-5 sm:p-6">
            <h2 className="font-heading font-bold text-dark text-lg">{tr("votreChauffeur")}</h2>
            <div className="flex items-center gap-4 mt-4">
              <div className="w-14 h-14 rounded-full bg-secondary/10 text-secondary flex items-center justify-center flex-shrink-0"><Car size={24} /></div>
              <div className="min-w-0">
                <p className="font-bold text-dark">{t.chauffeur.nom}</p>
                <p className="text-sm text-gray-600">{t.chauffeur.vehicule} · <span className="font-mono">{t.chauffeur.immatriculation}</span></p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              <a href={`tel:${t.chauffeur.telephone.replace(/\s/g, "")}`} className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-secondary text-white text-sm font-bold">
                <Phone size={15} /> {tr("appeler", { telephone: t.chauffeur.telephone })}
              </a>
              <a href={`https://wa.me/${t.chauffeur.telephone.replace(/\D/g, "")}`} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2.5 rounded-full border border-gray-200 text-dark text-sm font-bold">
                <MessageCircle size={15} /> WhatsApp<span className="sr-only"> ({tr("nouvelOnglet")})</span>
              </a>
            </div>
            <p className="text-xs text-gray-600 mt-3">{tr("pancarte")}</p>
          </section>
        )}

        <section className="bg-white rounded-3xl border border-gray-100 p-5 sm:p-6">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="flex gap-3"><Plane size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{tr("arrivee")}</dt><dd className="font-semibold text-dark">{dateVol(t.arrivee_locale)}</dd><dd className="text-gray-600">{tr("vol", { numero: t.numero_vol })} · {t.aeroport_detail.nom}</dd></div></div>
            <div className="flex gap-3"><MapPin size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{tr("destination")}</dt><dd className="font-semibold text-dark">{t.destination}</dd></div></div>
            <div className="flex gap-3"><Car size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{tr("vehicule")}</dt><dd className="font-semibold text-dark">{tT(`vehicules.${t.categorie}.nom`)}</dd></div></div>
            <div className="flex gap-3"><Users size={18} className="text-primary flex-shrink-0 mt-0.5" /><div><dt className="text-gray-600">{tT("passagersBagages")}</dt><dd className="font-semibold text-dark flex items-center gap-2">{t.passagers} <Luggage size={13} className="text-gray-500" /> {t.bagages}</dd></div></div>
          </dl>
          <div className="flex items-center justify-between mt-5 pt-4 border-t border-gray-100">
            <span className="text-gray-600 text-sm">{t.paiement === "reussi" ? tr("paye") : tr("prix")}</span>
            <span className="font-heading font-bold text-xl text-dark">{formatPrice(t.prix)}</span>
          </div>
          {t.remboursement && (
            t.remboursement.statut === "attente_numero" ? (
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-amber-900 bg-amber-50 rounded-xl px-3 py-2 mt-4">
                <span>{tR.rich("remboursementNumero", { montant: formatPrice(t.remboursement.montant), strong: (x) => <strong>{x}</strong> })}</span>
                <button onClick={() => setARembourser(t.remboursement!.montant)} className="px-4 py-1.5 rounded-full bg-secondary text-white text-xs font-bold">{tR("indiquerNumero")}</button>
              </div>
            ) : (
              <p className="text-sm text-dark bg-green-50 rounded-xl px-3 py-2 mt-4">
                {tR.rich(t.remboursement.statut === "envoye" ? "remboursementEffectue" : "remboursementEnCours", { montant: formatPrice(t.remboursement.montant), strong: (x) => <strong>{x}</strong> })}
              </p>
            )
          )}
          {t.paiement === "reussi" && <Documents objet="transfert" id={t.id} className="mt-4 pt-4 border-t border-gray-100" />}
        </section>

        {aPayer && (
          <section className="bg-white rounded-3xl border border-amber-200 p-5 sm:p-6">
            <h2 className="font-heading font-bold text-dark text-lg">{annuleParVoyageur || t.paiement === "annule" ? tP("paiementAnnule") : t.paiement === "echoue" ? tP("echoue") : tP("enAttente")}</h2>
            <p className="text-sm text-gray-600 mt-1">
              {tP("aucunDebit")}{minutes !== null && minutes > 0 && <> {tr.rich("gardee", { minutes, strong: (x) => <strong>{x}</strong> })}</>}
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              {moyens.map((m) => (
                <button key={m} disabled={envoi} onClick={() => payer(m)} className="px-5 py-2.5 rounded-full bg-secondary text-white text-sm font-bold disabled:opacity-60">
                  {tr("payerPar", { moyen: m === "mobile_money" ? "Mobile Money" : m === "carte" ? tr("carte") : "PayPal" })}
                </button>
              ))}
            </div>
          </section>
        )}

        {["en_attente_paiement", "confirme", "chauffeur_assigne"].includes(t.statut) && (
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-gray-600">
              {t.paiement === "reussi"
                ? t.annulation_gratuite ? tr("annulationGratuite") : tr("plusDeRemboursement")
                : ""}
            </p>
            <button onClick={annuler} disabled={annulation} className="px-5 py-2 rounded-full bg-red-50 text-red-700 font-semibold hover:bg-red-100 disabled:opacity-50">
              {annulation ? tr("annulation") : tr("annuler")}
            </button>
          </div>
        )}

        <p className="text-center text-sm">
          <Link href="/profil/transferts" className="text-primary font-bold hover:underline">{tr("mesTransferts")}</Link>
        </p>
      </div>

      {aRembourser !== null && (
        <CompteRemboursementDialog
          endpoint={adresseCompteRemboursement(t.id)}
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

export default function TransfertDetailPage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] bg-light" />}>
      <TransfertDetail />
    </Suspense>
  );
}
