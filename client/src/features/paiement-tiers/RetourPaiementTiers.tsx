"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { lireStatutTiers } from "./api";

// Beyond that, the server is no longer polled: the worker and the webhook take over
const ATTENTE_MAX_MS = 3 * 60 * 1000;

/** Return page of the payer after the provider's page: /payer/retour/<request>. */
export default function RetourPaiementTiers() {
  const t = useTranslations("paiementTiers");
  const { demande } = useParams<{ demande: string }>();
  const [debut] = useState(() => Date.now());
  const { data: statut, isError } = useQuery({
    queryKey: ["paiement-tiers", "statut", demande],
    queryFn: () => lireStatutTiers(demande),
    refetchInterval: (q) => {
      const s = q.state.data;
      const enCours = !s || (s.reservation !== "confirmed" && s.paiement === "en_attente");
      return enCours && Date.now() - debut < ATTENTE_MAX_MS ? 3000 : false;
    },
    retry: false,
  });

  let icone = <Loader2 size={32} className="animate-spin text-primary" />;
  let titre = t("verification");
  let texte = "";
  if (isError) {
    icone = <XCircle size={32} className="text-red-600" />;
    titre = t("introuvable");
  } else if (statut?.reservation === "confirmed") {
    icone = <CheckCircle2 size={32} className="text-secondary" />;
    titre = t("merci");
    texte = t("merciTexte", { voyageur: statut.voyageur });
  } else if (statut && statut.paiement !== "en_attente") {
    icone = <XCircle size={32} className="text-red-600" />;
    titre = t("nonAbouti");
    texte = t("nonAboutiTexte");
  } else if (statut && Date.now() - debut >= ATTENTE_MAX_MS) {
    icone = <Clock size={32} className="text-amber-600" />;
    titre = t("attenteLongue");
    texte = t("attenteLongueTexte");
  }

  return (
    <div className="bg-light min-h-[70vh]">
      <div className="max-w-xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
        <div className="bg-white rounded-3xl shadow-card border border-gray-100 p-6 sm:p-8 text-center" aria-live="polite">
          <div className="w-16 h-16 mx-auto rounded-full bg-gray-50 flex items-center justify-center mb-4">{icone}</div>
          <h1 className="font-heading font-bold text-dark text-2xl">{titre}</h1>
          {texte && <p className="text-gray-600 text-sm mt-2 max-w-md mx-auto">{texte}</p>}
          <Link href="/" className="inline-block mt-6 text-primary font-bold hover:underline">{t("accueil")}</Link>
        </div>
      </div>
    </div>
  );
}
