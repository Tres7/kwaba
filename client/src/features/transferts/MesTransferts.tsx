"use client";

import { listerMesTransferts } from "./api";
import { clesTransferts } from "./hooks";
import { Link } from "@/i18n/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Car, Plane, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StatutTransfert } from "./types";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

const LIBELLES: Record<StatutTransfert, { label: string; className: string }> = {
  en_attente_paiement: { label: "enAttente", className: "bg-amber-100 text-amber-800" },
  confirme: { label: "paye", className: "bg-blue-50 text-blue-800" },
  chauffeur_assigne: { label: "chauffeurAttribue", className: "bg-green-100 text-green-800" },
  termine: { label: "effectue", className: "bg-gray-100 text-dark" },
  annule: { label: "annule", className: "bg-red-100 text-red-700" },
};

export default function MesTransfertsPage() {
  const { dateVol, formatPrice } = useFormat();
  const tr = useTranslations("mesTransferts");
  const { data: transferts = [], isLoading } = useQuery({
    queryKey: clesTransferts.tous,
    queryFn: listerMesTransferts,
  });

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/profil" aria-label={tr("retourProfil")} className="w-10 h-10 rounded-full bg-white shadow-sm flex items-center justify-center text-dark hover:bg-light-muted">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">{tr("titre")}</h1>
            <p className="text-gray-600 text-sm mt-1">{tr("sousTitre")}</p>
          </div>
        </div>
        <Link href="/transfert" className="flex items-center gap-2 bg-primary text-white font-bold px-5 py-3 rounded-xl hover:bg-primary-600">
          <Plus size={18} /> {tr("reserver")}
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[0, 1].map((i) => <div key={i} className="h-28 skeleton rounded-2xl" />)}</div>
      ) : transferts.length === 0 ? (
        <div className="bg-white rounded-3xl border border-gray-100 p-10 sm:p-16 text-center">
          <Plane size={32} className="mx-auto text-primary mb-3" />
          <p className="text-gray-600 mb-4">{tr("aucun")}</p>
          <Link href="/transfert" className="inline-block bg-primary text-white font-bold px-6 py-3 rounded-xl">{tr("reserver")}</Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {transferts.map((t) => (
            <li key={t.id}>
              <Link href={`/transfert/${t.id}`} className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-card transition-shadow">
                <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Car size={22} /></div>
                <div className="flex-1 min-w-0">
                  <p className="font-heading font-bold text-dark">{t.aeroport_detail.ville} → {t.destination}</p>
                  <p className="text-sm text-gray-600 first-letter:uppercase">{dateVol(t.arrivee_locale)} · {tr("vol", { numero: t.numero_vol })}</p>
                  {t.chauffeur && <p className="text-sm text-dark mt-1">{tr("chauffeur", { nom: t.chauffeur.nom, telephone: t.chauffeur.telephone })}</p>}
                </div>
                <div className="flex sm:flex-col items-center sm:items-end justify-between gap-1">
                  <span className="font-heading font-bold text-dark">{formatPrice(t.prix)}</span>
                  <span className={cn("text-xs font-bold px-2.5 py-1 rounded-full", LIBELLES[t.statut].className)}>{tr(`statuts.${LIBELLES[t.statut].label}`)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
