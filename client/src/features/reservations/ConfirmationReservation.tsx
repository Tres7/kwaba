"use client";

import { useReservation } from "./hooks";
import { Link, useRouter } from "@/i18n/navigation";
import { useEffect } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { CheckCircle, Calendar, MapPin, Users, ArrowRight, MessageCircle, Plane } from "lucide-react";
import { FALLBACK_IMAGE } from "@/lib/utils";
import { Documents } from "@/features/documents";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

const PAYMENT_LABELS: Record<string, string> = {
  mobile_money: "mobileMoney",
  carte: "carte",
  paypal: "paypal",
};

export default function ConfirmationPage() {
  const { formatDate, formatPrice } = useFormat();
  const t = useTranslations("paiement");
  const tRes = useTranslations("reservation");
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const { data: reservation, isLoading, isError } = useReservation(params.id);

  // Booking not paid yet: back to the payment page
  useEffect(() => {
    if (reservation?.status === "pending" && reservation.expire_le) router.replace(`/reservation/paiement/${reservation.id}`);
  }, [reservation, router]);

  if (isLoading) {
    return <div className="max-w-3xl mx-auto px-4 py-16"><div className="h-80 skeleton rounded-3xl" /></div>;
  }

  if (isError || !reservation) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
        <Link href="/profil/reservations" className="text-primary font-bold hover:underline">{t("voirMesReservations")}</Link>
      </div>
    );
  }

  const h = reservation.hebergement_detail;
  const longDate = { day: "numeric", month: "long" } as const;

  return (
    <div className="bg-light">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
        <motion.div className="text-center mb-10" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut" }}>
          <div className="relative w-20 h-20 mx-auto mb-6">
            {[0, 1].map((i) => (
              <motion.div key={i} className="absolute inset-0 rounded-full bg-green-400/30" initial={{ scale: 0.6, opacity: 0.7 }} animate={{ scale: 2.4, opacity: 0 }} transition={{ duration: 1.2, delay: i * 0.4, repeat: 2, repeatDelay: 0.8, ease: "easeOut" }} />
            ))}
            <motion.div className="relative w-20 h-20 bg-green-100 rounded-full flex items-center justify-center" initial={{ scale: 0, rotate: -20 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 220, damping: 14, delay: 0.15 }}>
              <CheckCircle size={40} className="text-green-600" />
            </motion.div>
          </div>
          <h1 className="font-heading font-bold text-dark text-3xl md:text-4xl mb-3">
            {reservation.status === "cancelled" ? t("annulee") : t("confirmee")}
          </h1>
          <p className="text-gray-500 text-base max-w-lg mx-auto">
            {t("confirmeeTexte")}
          </p>
        </motion.div>

        <motion.div className="bg-white rounded-3xl shadow-card border border-gray-100 p-5 sm:p-8 mb-10" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.4 }}>
          <div className="flex flex-col md:flex-row gap-6">
            <img src={h.image_url || FALLBACK_IMAGE} alt={h.name} className="w-full md:w-48 h-44 md:h-auto rounded-2xl object-cover flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-3 mb-4">
                <div className="min-w-0">
                  <h2 className="font-heading font-bold text-dark text-xl">{h.name}</h2>
                  <p className="flex items-center gap-1.5 text-gray-500 text-sm mt-1"><MapPin size={14} className="text-primary flex-shrink-0" />{h.location ? `${h.location}, ` : ""}{h.city}</p>
                </div>
                <span className={reservation.status === "cancelled" ? "bg-red-100 text-red-700 text-xs font-bold px-3 py-1.5 rounded-full" : "bg-green-100 text-green-700 text-xs font-bold px-3 py-1.5 rounded-full"}>
                  {reservation.status === "cancelled" ? t("statutAnnulee") : reservation.status === "pending" ? t("statutEnAttente") : t("statutConfirmee")}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-4 border-t border-gray-100">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0"><Calendar size={18} className="text-primary" /></div>
                  <div>
                    <p className="text-xs text-gray-500">{tRes("dates")}</p>
                    <p className="text-sm font-bold text-dark">{formatDate(reservation.check_in, longDate)} – {formatDate(reservation.check_out, longDate)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0"><Users size={18} className="text-primary" /></div>
                  <div>
                    <p className="text-xs text-gray-500">{tRes("voyageurs")}</p>
                    <p className="text-sm font-bold text-dark">{t("personnes", { nombre: reservation.guests_count })}</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500">
                    {reservation.paiement === "reussi" ? t("paye") : t("total")} ({tRes(`moyens.${PAYMENT_LABELS[reservation.payment_method] ?? "mobileMoney"}`)})
                  </p>
                  <p className="text-lg font-heading font-bold text-primary">{formatPrice(reservation.total_price)}</p>
                </div>
              </div>

              {reservation.remboursement && (
                <p className="mt-4 text-sm text-dark bg-green-50 rounded-xl px-4 py-3">
                  {t.rich(reservation.remboursement.statut === "envoye" ? "remboursementEffectue" : reservation.remboursement.statut === "attente_numero" ? "remboursementNumero" : "remboursementEnCours", {
                    montant: formatPrice(reservation.remboursement.montant), strong: (x) => <strong>{x}</strong>,
                  })}
                </p>
              )}

              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs text-gray-500">{t("numero")}</p>
                <p className="text-sm font-mono font-bold text-dark">{reservation.reference}</p>
                {reservation.paiement === "reussi" && <Documents objet="reservation" id={reservation.id} className="mt-3" />}
              </div>
            </div>
          </div>
        </motion.div>

        {reservation.status === "confirmed" && (
          <Link href={`/transfert?reservation=${reservation.id}`}
            className="mb-8 flex items-center gap-4 bg-dark text-white rounded-3xl p-5 sm:p-6 hover:bg-dark/90 transition-colors">
            <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center flex-shrink-0"><Plane size={22} /></div>
            <div className="flex-1 min-w-0">
              <p className="font-heading font-bold">{t("chauffeurTitre")}</p>
              <p className="text-sm text-white/80">{t("chauffeurTexte", { ville: h.city })}</p>
            </div>
            <ArrowRight size={20} className="flex-shrink-0" />
          </Link>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/profil/reservations" className="bg-primary text-white font-bold px-8 py-4 rounded-full text-center shadow-button hover:bg-primary-600 transition-colors flex items-center justify-center gap-2">
            {t("mesReservations")} <ArrowRight size={16} />
          </Link>
          <Link href={`/hebergements/${h.id}`} className="bg-white border border-gray-200 text-dark font-bold px-8 py-4 rounded-full text-center hover:bg-gray-50 transition-colors flex items-center justify-center gap-2">
            <MessageCircle size={16} /> {t("contacterHote")}
          </Link>
        </div>
      </div>
    </div>
  );
}
