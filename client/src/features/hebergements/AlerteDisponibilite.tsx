"use client";

import { creerAlerte } from "./api";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { BellRing, Check } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { useLocale, useTranslations } from "next-intl";

interface Props {
  hebergementId: string;
  checkIn: string;
  checkOut: string;
  typeLogement?: string;
  nbUnites?: number;
}

/** "Notify me if these dates become free", under full dates. Without an account, the address is confirmed by email. */
export default function AlerteDisponibilite({ hebergementId, checkIn, checkOut, typeLogement, nbUnites = 1 }: Props) {
  const t = useTranslations("alerte");
  const locale = useLocale();
  const { status } = useSession();
  const connecte = status === "authenticated";
  const [ouvert, setOuvert] = useState(false);
  const [email, setEmail] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [resultat, setResultat] = useState<{ statut: "active" | "a_confirmer"; email: string } | null>(null);

  const creer = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setEnvoi(true);
    try {
      setResultat(await creerAlerte(hebergementId, {
        debut: checkIn, fin: checkOut, nb_unites: nbUnites, langue: locale,
        ...(typeLogement ? { type_logement: typeLogement } : {}),
        ...(connecte ? {} : { email: email.trim() }),
      }));
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setEnvoi(false);
    }
  };

  if (resultat) {
    return (
      <p role="status" className="text-sm text-green-800 bg-green-50 rounded-xl p-3 mb-3 flex gap-2">
        <Check size={16} className="flex-shrink-0 mt-0.5" aria-hidden />
        <span>{resultat.statut === "active" ? t("active", { email: resultat.email }) : t("aConfirmer", { email: resultat.email })}</span>
      </p>
    );
  }

  if (!ouvert && !connecte) {
    return (
      <button type="button" onClick={() => setOuvert(true)}
        className="w-full mb-3 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-primary text-primary text-sm font-semibold hover:bg-primary/5">
        <BellRing size={16} aria-hidden /> {t("bouton")}
      </button>
    );
  }

  if (connecte) {
    return (
      <button type="button" onClick={() => creer()} disabled={envoi}
        className="w-full mb-3 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-primary text-primary text-sm font-semibold hover:bg-primary/5 disabled:opacity-50">
        <BellRing size={16} aria-hidden /> {envoi ? "..." : t("bouton")}
      </button>
    );
  }

  return (
    <form onSubmit={creer} className="mb-3 border border-gray-200 rounded-xl p-3 space-y-2">
      <label className="block text-sm text-dark">
        {t("emailLibelle")}
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2.5 text-base sm:text-sm outline-none focus:border-primary" />
      </label>
      <p className="text-xs text-gray-500">{t("emailAide")}</p>
      <button type="submit" disabled={envoi} className="w-full py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-50">
        {envoi ? "..." : t("valider")}
      </button>
    </form>
  );
}
