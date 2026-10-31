"use client";

import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Calendar, MapPin, CheckCircle, Clock, XCircle, Users, Star, CreditCard } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { cn, FALLBACK_IMAGE, isoDate } from "@/lib/utils";
import PropertyCard from "@/components/hebergement/PropertyCard";
import CompteRemboursementDialog from "@/components/paiement/CompteRemboursementDialog";
import Documents from "@/features/documents/Documents";
import type { Hebergement, Paginated, Reservation } from "@/types/api/models";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

const TABS = [
  { id: "upcoming", label: "aVenir" },
  { id: "past", label: "passees" },
  { id: "cancelled", label: "annulees" },
] as const;

type Tab = (typeof TABS)[number]["id"];

const tabFor = (r: Reservation): Tab => {
  if (r.status === "cancelled") return "cancelled";
  return r.check_out >= isoDate() ? "upcoming" : "past";
};

const STATUS = {
  confirmed: { label: "confirmee", icon: CheckCircle, className: "bg-green-100 text-green-700" },
  pending: { label: "enAttente", icon: Clock, className: "bg-amber-100 text-amber-800" },
  cancelled: { label: "annulee", icon: XCircle, className: "bg-red-100 text-red-700" },
};

export default function ReservationsPage() {
  const { formatDate, formatPrice } = useFormat();
  const t = useTranslations("mesReservations");
  const tVoy = useTranslations("voyageurs");
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("upcoming");
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [aRembourser, setARembourser] = useState<{ id: string; montant: number } | null>(null);

  const { data: reservations = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["reservations"],
    queryFn: async () => (await api.get<Paginated<Reservation>>("/v1/reservations/")).data.results,
  });

  // Recommendations: best rated listings not already booked
  const { data: recommended = [] } = useQuery({
    queryKey: ["hebergements", "recommandes-profil"],
    queryFn: async () => (await api.get<Paginated<Hebergement>>("/v1/hebergements/", { params: { sort: "note", limit: 8 } })).data.results,
  });
  const reservedIds = new Set(reservations.map((r) => r.hebergement_detail.id));
  const suggestions = recommended.filter((h) => !reservedIds.has(h.id)).slice(0, 3);

  const handleCancel = async (r: Reservation) => {
    const question = r.paiement === "reussi"
      ? `${t("annulerQuestion", { nom: r.hebergement_detail.name })}\n\n${t("annulerBareme")}`
      : t("annulerQuestion", { nom: r.hebergement_detail.name });
    if (!window.confirm(question)) return;
    setCancellingId(r.id);
    try {
      const res = await api.delete<{ rembourse?: number; numero_requis?: boolean }>(`/v1/reservations/${r.id}/`);
      queryClient.invalidateQueries({ queryKey: ["reservations"] });
      const rembourse = res.data.rembourse ?? 0;
      toast.success(rembourse > 0 ? t("annuleeRembourse", { montant: formatPrice(rembourse) }) : t("annuleeToast"));
      if (res.data.numero_requis) setARembourser({ id: r.id, montant: rembourse });
    } catch (err) {
      toast.error(apiErrorMessage(err, t("erreurAnnulation")));
    } finally {
      setCancellingId(null);
    }
  };

  const counts = Object.fromEntries(TABS.map((t) => [t.id, reservations.filter((r) => tabFor(r) === t.id).length])) as Record<Tab, number>;
  const filtered = reservations.filter((r) => tabFor(r) === activeTab);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <div className="mb-8 flex items-center gap-4">
        <Link href="/profil" aria-label={t("retourProfil")} className="w-10 h-10 rounded-full bg-white shadow-sm flex items-center justify-center text-dark hover:bg-light-muted transition-colors flex-shrink-0">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">{t("titre")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("sousTitre")}</p>
        </div>
      </div>

      <div className="flex gap-6 border-b border-gray-200 mb-6 overflow-x-auto scrollbar-hide" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn("pb-3 text-sm font-bold transition-colors whitespace-nowrap border-b-2", activeTab === tab.id ? "text-primary border-primary" : "text-gray-400 border-transparent hover:text-dark")}
          >
            {t(`onglets.${tab.label}`)}{counts[tab.id] > 0 && <span className="ml-1.5 text-xs">({counts[tab.id]})</span>}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {isLoading ? (
          [0, 1].map((i) => <div key={i} className="h-48 skeleton rounded-2xl" />)
        ) : isError ? (
          <div className="bg-white rounded-3xl p-12 text-center">
            <p className="text-red-600 font-medium mb-2">{t("erreurChargement")}</p>
            <button onClick={() => refetch()} className="text-primary font-bold hover:underline">{t("reessayer")}</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-3xl border border-gray-100 p-10 sm:p-16 text-center">
            <p className="text-gray-500 font-medium mb-4">{t("aucune")}</p>
            {activeTab === "upcoming" && <Link href="/recherche" className="inline-block bg-primary text-white font-bold px-6 py-3 rounded-xl">{t("trouver")}</Link>}
          </div>
        ) : (
          filtered.map((res) => {
            const status = STATUS[res.status];
            const canCancel = res.status !== "cancelled" && res.check_in > isoDate();
            return (
              <article key={res.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col sm:flex-row hover:shadow-card transition-shadow">
                <Link href={`/hebergements/${res.hebergement_detail.id}`} className="w-full sm:w-48 md:w-56 h-44 sm:h-auto flex-shrink-0">
                  <img src={res.hebergement_detail.image_url || FALLBACK_IMAGE} alt={res.hebergement_detail.name} className="w-full h-full object-cover" />
                </Link>
                <div className="flex-1 p-5 sm:p-6 flex flex-col justify-between min-w-0">
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="min-w-0">
                        <h2 className="font-heading font-bold text-lg text-dark truncate">{res.hebergement_detail.name}</h2>
                        <p className="flex items-center gap-1.5 text-gray-500 text-sm mt-1"><MapPin size={14} className="text-primary flex-shrink-0" />{res.hebergement_detail.city}</p>
                      </div>
                      <span className={cn("flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full flex-shrink-0", status.className)}>
                        <status.icon size={12} /> {t(`statuts.${status.label}`)}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-gray-600">
                      <span className="flex items-center gap-2"><Calendar size={14} className="text-primary" />{formatDate(res.check_in)} → {formatDate(res.check_out)}</span>
                      <span className="flex items-center gap-2"><Users size={14} className="text-primary" />{tVoy("voyageurs", { nombre: res.guests_count })}</span>
                    </div>
                    <p className="text-xs text-gray-500 font-mono mt-2">{res.reference}</p>
                    {res.status === "pending" && res.expire_le && (
                      <p className="text-sm text-amber-800 bg-amber-50 rounded-xl px-3 py-2 mt-3">
                        {t("aRegler")}
                      </p>
                    )}
                    {res.remboursement && (res.remboursement.statut === "attente_numero" ? (
                      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-amber-900 bg-amber-50 rounded-xl px-3 py-2 mt-3">
                        <span>{t.rich("remboursementNumero", { montant: formatPrice(res.remboursement.montant), strong: (x) => <strong>{x}</strong> })}</span>
                        <button
                          onClick={() => setARembourser({ id: res.id, montant: res.remboursement!.montant })}
                          className="px-4 py-1.5 rounded-full bg-secondary text-white text-xs font-bold hover:bg-secondary-600"
                        >
                          {t("indiquerNumero")}
                        </button>
                      </div>
                    ) : (
                      <p className="text-sm text-dark bg-green-50 rounded-xl px-3 py-2 mt-3">
                        {t.rich(res.remboursement.statut === "envoye" ? "remboursementEffectue" : "remboursementEnCours", { montant: formatPrice(res.remboursement.montant), strong: (x) => <strong>{x}</strong> })}
                      </p>
                    ))}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 mt-5 pt-4 border-t border-gray-100">
                    <div>
                      <span className="text-xs text-gray-500">{res.paiement === "reussi" ? t("paye") : t("total")}</span>
                      <p className="font-heading font-bold text-lg text-dark">{formatPrice(res.total_price)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {res.status === "pending" && res.expire_le && (
                        <Link href={`/reservation/paiement/${res.id}`} className="flex items-center gap-1.5 px-5 py-2 bg-secondary text-white text-sm font-bold rounded-full hover:bg-secondary-600 transition-colors">
                          <CreditCard size={14} /> Payer
                        </Link>
                      )}
                      {res.peut_evaluer && (
                        <Link href={`/profil/reservations/${res.id}/avis`} className="flex items-center gap-1.5 px-5 py-2 bg-primary text-white text-sm font-bold rounded-full hover:bg-primary-600 transition-colors">
                          <Star size={14} className="fill-white" /> Laisser un avis
                        </Link>
                      )}
                      {res.avis_id && (
                        <Link href={`/hebergements/${res.hebergement_detail.id}#avis`} className="flex items-center gap-1.5 px-4 py-2 text-secondary text-sm font-semibold">
                          <CheckCircle size={14} /> {t("avisPublie")}
                        </Link>
                      )}
                      <Link href={`/reservation/confirmation/${res.id}`} className="px-5 py-2 bg-gray-100 text-dark text-sm font-medium rounded-full hover:bg-gray-200 transition-colors">
                        {t("details")}
                      </Link>
                      {canCancel && (
                        <button onClick={() => handleCancel(res)} disabled={cancellingId === res.id} className="px-5 py-2 bg-red-50 text-red-700 text-sm font-medium rounded-full hover:bg-red-100 transition-colors disabled:opacity-50">
                          {cancellingId === res.id ? t("annulation") : t("annuler")}
                        </button>
                      )}
                    </div>
                  </div>
                  {res.paiement === "reussi" && <Documents objet="reservation" id={res.id} className="mt-3" />}
                </div>
              </article>
            );
          })
        )}
      </div>

      {aRembourser && (
        <CompteRemboursementDialog
          endpoint={`/v1/paiements/reservations/${aRembourser.id}/compte-remboursement/`}
          montant={aRembourser.montant}
          onClose={() => setARembourser(null)}
          onDone={() => {
            setARembourser(null);
            queryClient.invalidateQueries({ queryKey: ["reservations"] });
            toast.success(t("numeroEnregistre"));
          }}
        />
      )}

      {suggestions.length > 0 && (
        <section className="mt-12">
          <h2 className="font-heading font-bold text-xl text-dark mb-6">{t("recommande")}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {suggestions.map((h) => <PropertyCard key={h.id} property={h} />)}
          </div>
        </section>
      )}
    </div>
  );
}
