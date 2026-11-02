"use client";

import { useMesReservations } from "@/features/reservations";
import { Link } from "@/i18n/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { modifierVoyage, partagerReservation, retirerReservation } from "./api";
import { messageErreur } from "./erreurs";
import type { SectionVoyage } from "./types";

export default function Reservations({ v, appliquer, recharger }: SectionVoyage) {
  const { formatDate, formatPrice } = useFormat();
  const t = useTranslations("voyage");
  const tVoy = useTranslations("voyageurs");
  const [notes, setNotes] = useState(v.notes);
  const [sauvegarde, setSauvegarde] = useState(false);
  const { data: mesReservations = [] } = useMesReservations();
  const partagees = new Set(v.reservations.map((r) => r.reservation_id));
  const aPartager = mesReservations.filter((r) => r.status !== "cancelled" && !partagees.has(r.id));

  const enregistrerNotes = async () => {
    setSauvegarde(true);
    try {
      appliquer(await modifierVoyage(v.id, { notes }));
      toast.success(t("infosEnregistrees"));
    } catch (err) {
      toast.error(messageErreur(err, t("enregistrementImpossible")));
    } finally {
      setSauvegarde(false);
    }
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-3">
        {v.reservations.length === 0 ? (
          <p className="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-600">{t("aucuneResa")}</p>
        ) : v.reservations.map((r) => (
          <article key={r.id} className="bg-white rounded-2xl border border-gray-100 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link href={`/hebergements/${r.hebergement_id}`} className="font-heading font-bold text-dark hover:text-primary">{r.hebergement}</Link>
                <p className="text-sm text-gray-600">{[r.adresse, r.ville].filter(Boolean).join(", ")}</p>
              </div>
              <span className={cn("text-xs font-bold px-2.5 py-1 rounded-full", r.statut === "confirmed" ? "bg-green-100 text-green-800" : r.statut === "pending" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-700")}>
                {r.statut === "confirmed" ? t("confirmee") : r.statut === "pending" ? t("enAttente") : t("annulee")}
              </span>
            </div>
            <p className="text-sm text-dark mt-2">{formatDate(r.check_in)} → {formatDate(r.check_out)} · {tVoy("voyageurs", { nombre: r.voyageurs })} · {formatPrice(r.total)}</p>
            <div className="flex items-center justify-between mt-2">
              <p className="text-xs text-gray-600">{t("reservePar", { nom: r.reserve_par })} · <span className="font-mono">{r.reference}</span></p>
              {r.peut_retirer && (
                <button onClick={async () => { await retirerReservation(v.id, r.id); recharger(); }} className="text-xs text-gray-600 hover:text-red-700 underline">{t("nePlusPartager")}</button>
              )}
            </div>
          </article>
        ))}
        {aPartager.length > 0 && (
          <section className="bg-white rounded-2xl border border-dashed border-gray-300 p-5">
            <h3 className="font-bold text-dark text-sm">{t("partagerResa")}</h3>
            <ul className="mt-2 space-y-2">
              {aPartager.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate">{r.hebergement_detail.name} · {formatDate(r.check_in)} → {formatDate(r.check_out)}</span>
                  <button onClick={async () => {
                    try { appliquer(await partagerReservation(v.id, r.id)); }
                    catch (err) { toast.error(messageErreur(err, t("partageImpossible"))); }
                  }} className="px-3 py-1.5 rounded-full bg-primary text-white text-xs font-bold flex-shrink-0">{t("partager")}</button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
      <section className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-5 h-fit">
        <label htmlFor="v-notes" className="font-heading font-bold text-dark">{t("infosPratiques")}</label>
        <p className="text-xs text-gray-600 mt-1">{t("infosPratiquesTexte")}</p>
        <textarea id="v-notes" rows={8} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={4000}
          className="w-full mt-3 bg-gray-50 border border-gray-200 rounded-xl p-3 text-base sm:text-sm outline-none focus:border-primary/50 resize-y" />
        <button onClick={enregistrerNotes} disabled={sauvegarde || notes === v.notes} className="w-full mt-3 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-50">
          {sauvegarde ? t("enregistrement") : t("enregistrer")}
        </button>
      </section>
    </div>
  );
}
