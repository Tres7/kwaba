"use client";

import FormField from "@/components/ui/FormField";
import { useRouter } from "@/i18n/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Crown, MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { modifierVoyage, nouveauLien, retirerMembre, supprimerVoyage } from "./api";
import { messageErreur } from "./erreurs";
import { clesVoyages } from "./hooks";
import type { Voyage } from "./types";

export default function Membres({ v, recharger }: { v: Voyage; recharger: () => void }) {
  const t = useTranslations("voyage");
  const tT = useTranslations("together");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [copie, setCopie] = useState(false);
  const [dates, setDates] = useState({ date_debut: v.date_debut ?? "", date_fin: v.date_fin ?? "", nb_voyageurs: v.nb_voyageurs });
  const lien = typeof window !== "undefined" ? `${window.location.origin}/together/rejoindre/${v.code_invitation}` : "";
  const texte = t("messageInvitation", { nom: v.nom, destination: v.destination, lien });

  const copier = async () => {
    try {
      await navigator.clipboard.writeText(lien);
      setCopie(true);
      setTimeout(() => setCopie(false), 2500);
    } catch {
      toast.error(t("copieImpossible"));
    }
  };

  const retirer = async (id: string, nom: string, moi: boolean) => {
    if (!window.confirm(moi ? t("quitterQuestion") : t("retirerQuestion", { nom }))) return;
    try {
      await retirerMembre(v.id, id);
      if (moi) {
        queryClient.invalidateQueries({ queryKey: clesVoyages.tous });
        router.push("/together");
      } else recharger();
    } catch (err) {
      toast.error(messageErreur(err, t("actionImpossible")));
    }
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-5">
        <section className="bg-white rounded-2xl border border-gray-100 p-5">
          <h3 className="font-heading font-bold text-dark">{t("inviter")}</h3>
          <p className="text-sm text-gray-600 mt-1">{t("inviterTexte")}</p>
          <div className="flex gap-2 mt-3">
            <input readOnly value={lien} aria-label={t("lienInvitation")} onFocus={(e) => e.target.select()}
              className="flex-1 min-w-0 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm text-dark" />
            <button onClick={copier} className="flex items-center gap-1.5 px-4 rounded-xl border border-gray-200 text-sm font-bold text-dark hover:bg-gray-50">
              {copie ? <Check size={15} className="text-secondary" /> : <Copy size={15} />} {copie ? t("copie") : t("copier")}
            </button>
          </div>
          <a href={`https://wa.me/?text=${encodeURIComponent(texte)}`} target="_blank" rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#1D7A4C] text-white text-sm font-bold">
            <MessageCircle size={15} /> {t("whatsapp")}<span className="sr-only"> ({t("nouvelOnglet")})</span>
          </a>
          {v.est_organisateur && (
            <button onClick={async () => { await nouveauLien(v.id); recharger(); toast.success(t("nouveauLien")); }}
              className="block mt-3 text-xs text-gray-600 underline hover:text-dark">{t("desactiverLien")}</button>
          )}
        </section>

        <section className="bg-white rounded-2xl border border-gray-100 p-5">
          <h3 className="font-heading font-bold text-dark">{tT("membres", { nombre: v.membres.length })}</h3>
          <ul className="mt-3 divide-y divide-gray-100">
            {v.membres.map((m) => (
              <li key={m.id} className="flex items-center justify-between gap-3 py-2.5">
                <span className="flex items-center gap-2 text-sm text-dark">
                  {m.nom}{m.moi && ` (${t("vous")})`}
                  {m.organisateur && <span className="flex items-center gap-1 text-xs font-bold text-primary"><Crown size={12} /> {t("organise")}</span>}
                </span>
                {!m.organisateur && (m.moi || v.est_organisateur) && (
                  <button onClick={() => retirer(m.id, m.nom, m.moi)} className="text-xs text-gray-600 hover:text-red-700 underline">{m.moi ? t("quitter") : t("retirer")}</button>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {v.est_organisateur && (
        <section className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-5 h-fit space-y-3">
          <h3 className="font-heading font-bold text-dark">{t("datesTaille")}</h3>
          <div className="grid grid-cols-2 gap-3">
            <FormField label={tT("arrivee")} id="m-debut" type="date" value={dates.date_debut} onChange={(e) => setDates({ ...dates, date_debut: e.target.value })} />
            <FormField label={tT("depart")} id="m-fin" type="date" value={dates.date_fin} onChange={(e) => setDates({ ...dates, date_fin: e.target.value })} />
          </div>
          <FormField label={t("voyageurs")} id="m-nb" type="number" min={1} max={20} value={dates.nb_voyageurs}
            onChange={(e) => setDates({ ...dates, nb_voyageurs: Number(e.target.value) })} />
          <button onClick={async () => {
            try {
              await modifierVoyage(v.id, { ...dates, date_debut: dates.date_debut || null, date_fin: dates.date_fin || null });
              recharger();
              toast.success(t("misAJour"));
            } catch (err) { toast.error(messageErreur(err, t("majImpossible"))); }
          }} className="w-full py-2.5 rounded-xl bg-primary text-white text-sm font-bold">{t("enregistrer")}</button>
          <button onClick={async () => {
            if (!window.confirm(t("supprimerQuestion", { nom: v.nom }))) return;
            await supprimerVoyage(v.id);
            queryClient.invalidateQueries({ queryKey: clesVoyages.tous });
            router.push("/together");
          }} className="w-full py-2.5 rounded-xl border border-red-200 text-red-700 text-sm font-bold hover:bg-red-50">{t("supprimerVoyage")}</button>
        </section>
      )}
    </div>
  );
}
