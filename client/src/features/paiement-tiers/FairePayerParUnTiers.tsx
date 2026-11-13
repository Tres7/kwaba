"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, HandCoins, MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { apiErrorMessage } from "@/lib/api";
import { useFormat } from "@/lib/format";
import { creerLienTiers, desactiverLienTiers, lireDemandeTiers } from "./api";

const HEURE: Intl.DateTimeFormatOptions = { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" };

/**
 * On the traveller's payment page: ask someone else to pay the stay. The secret link is shown once, when it is
 * created; `onActif` tells the page that a request is open (it then follows the booking's status).
 */
export default function FairePayerParUnTiers({ reservationId, onActif }: { reservationId: string; onActif?: (actif: boolean) => void }) {
  const t = useTranslations("paiementTiers");
  const { formatDate } = useFormat();
  const queryClient = useQueryClient();
  const cle = ["paiement-tiers", "demande", reservationId];
  const { data: demande } = useQuery({ queryKey: cle, queryFn: () => lireDemandeTiers(reservationId) });
  const [lien, setLien] = useState("");
  const [ouvert, setOuvert] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [copie, setCopie] = useState(false);

  useEffect(() => { onActif?.(!!demande?.active); }, [demande?.active, onActif]);

  const creer = async () => {
    setEnvoi(true);
    try {
      const nouvelle = await creerLienTiers(reservationId);
      setLien(nouvelle.lien ?? "");
      queryClient.setQueryData(cle, nouvelle);
    } catch (err) {
      toast.error(apiErrorMessage(err, t("lienImpossible")));
    } finally {
      setEnvoi(false);
    }
  };

  const desactiver = async () => {
    try {
      await desactiverLienTiers(reservationId);
      setLien("");
      queryClient.setQueryData(cle, { active: false, expire_le: null, groupe: false });
      toast.success(t("lienDesactive"));
    } catch (err) {
      toast.error(apiErrorMessage(err, t("lienImpossible")));
    }
  };

  const copier = async () => {
    try {
      await navigator.clipboard.writeText(lien);
      setCopie(true);
      setTimeout(() => setCopie(false), 2500);
    } catch {
      toast.error(t("copieImpossible"));
    }
  };

  if (!demande) return null;

  if (!demande.active && !ouvert) {
    return (
      <button type="button" onClick={() => setOuvert(true)}
        className="w-full mt-4 flex items-center justify-center gap-2 py-3 rounded-2xl border border-primary/30 text-brand text-sm font-bold hover:bg-primary/5">
        <HandCoins size={17} /> {t("fairePayer")}
      </button>
    );
  }

  return (
    <section className="mt-6 rounded-2xl border border-primary/20 bg-primary/5 p-4" aria-labelledby="faire-payer">
      <h2 id="faire-payer" className="flex items-center gap-2 font-heading font-bold text-dark"><HandCoins size={18} className="text-brand" /> {t("fairePayer")}</h2>
      <p className="text-sm text-gray-700 mt-1">{t("explication")}</p>

      {lien ? (
        <>
          <div className="flex gap-2 mt-3">
            <input readOnly value={lien} aria-label={t("lienPaiement")} onFocus={(e) => e.target.select()}
              className="flex-1 min-w-0 bg-surface border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-dark" />
            <button type="button" onClick={copier} className="flex items-center gap-1.5 px-4 rounded-xl border border-gray-200 bg-surface text-sm font-bold text-dark hover:bg-gray-50">
              {copie ? <Check size={15} className="text-secondary" /> : <Copy size={15} />} {copie ? t("copie") : t("copier")}
            </button>
          </div>
          <a href={`https://wa.me/?text=${encodeURIComponent(t("messageWhatsapp", { lien }))}`} target="_blank" rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#1D7A4C] text-white text-sm font-bold">
            <MessageCircle size={15} /> {t("whatsapp")}<span className="sr-only"> ({t("nouvelOnglet")})</span>
          </a>
          <p className="text-xs text-gray-600 mt-3">{t("lienUneFois")}</p>
        </>
      ) : demande.active ? (
        <p className="text-sm text-dark mt-3">{t("lienActif", { date: formatDate(demande.expire_le ?? "", HEURE) })}</p>
      ) : null}

      {lien && demande.active && <p className="text-xs text-gray-600 mt-2">{t("validite", { date: formatDate(demande.expire_le ?? "", HEURE) })}</p>}

      <div className="flex flex-wrap gap-3 mt-4">
        <button type="button" onClick={creer} disabled={envoi}
          className="px-4 py-2.5 rounded-full bg-primary text-white text-sm font-bold disabled:opacity-60">
          {demande.active ? t("nouveauLien") : t("creerLien")}
        </button>
        {demande.active && (
          <button type="button" onClick={desactiver} className="text-sm text-gray-600 underline hover:text-red-700">{t("desactiver")}</button>
        )}
      </div>
    </section>
  );
}
