"use client";

import { Suspense, useState } from "react";
import { Link } from "@/i18n/navigation";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, CheckCircle, HandHeart, Loader2, XCircle } from "lucide-react";
import api from "@/lib/api";
import type { Don } from "@/types/api/give";
import Documents from "@/components/documents/Documents";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

const ATTENTE_MAX_MS = 3 * 60 * 1000;

function RetourDon() {
  const { formatDate, formatPrice } = useFormat();
  const t = useTranslations("retourDon");
  const { id } = useParams<{ id: string }>();
  const annule = useSearchParams().get("annule") === "1";
  const [debut] = useState(() => Date.now());

  const { data: don, isError } = useQuery({
    queryKey: ["give", "don", id],
    queryFn: async () => (await api.get<Don>(`/v1/give/dons/${id}/`)).data,
    refetchInterval: (q) => (q.state.data?.statut === "en_attente" && !annule && Date.now() - debut < ATTENTE_MAX_MS ? 3000 : false),
    retry: false,
  });

  if (isError) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
        <Link href="/profil/dons" className="text-primary font-bold hover:underline">{t("mesDons")}</Link>
      </div>
    );
  }
  if (!don) return <div className="max-w-xl mx-auto px-4 py-10"><div className="h-80 skeleton rounded-3xl" /></div>;

  const enAttente = don.statut === "en_attente" && !annule && Date.now() - debut < ATTENTE_MAX_MS;
  const echoue = don.statut === "echoue" || (don.statut === "en_attente" && !enAttente);

  return (
    <div className="bg-light min-h-[70vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-xl bg-white rounded-3xl shadow-card border border-gray-100 p-6 sm:p-8" aria-live="polite">
        {don.statut === "paye" ? (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto rounded-full bg-secondary/10 text-secondary flex items-center justify-center"><HandHeart size={30} /></div>
            <h1 className="font-heading font-bold text-dark text-2xl mt-4">{t("merci")}</h1>
            <p className="text-gray-600 mt-2">
              {t.rich(don.projet ? "irontProjet" : "iront", { montant: formatPrice(don.montant_ong), nom: don.organisation.nom, projet: don.projet?.titre ?? "", strong: (x) => <strong className="text-dark">{x}</strong> })}
            </p>
          </div>
        ) : enAttente ? (
          <div className="text-center">
            <Loader2 size={36} className="mx-auto animate-spin text-primary" />
            <h1 className="font-heading font-bold text-dark text-xl mt-4">{t("confirmation")}</h1>
            <p className="text-sm text-gray-600 mt-2">{t("mobileMoney")}</p>
          </div>
        ) : echoue && (
          <div className="text-center">
            <XCircle size={40} className="mx-auto text-red-600" />
            <h1 className="font-heading font-bold text-dark text-xl mt-4">{annule ? t("annule") : t("echoue")}</h1>
            <p className="text-sm text-gray-600 mt-2">{t("echoueTexte")}</p>
            <Link href={`/give/${don.organisation.slug}#don`} className="inline-block mt-5 bg-secondary text-white font-bold px-6 py-3 rounded-xl">{t("reessayer")}</Link>
          </div>
        )}

        <dl className="mt-6 rounded-2xl bg-light p-4 text-sm space-y-1.5">
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("reference")}</dt><dd className="font-mono text-dark">{don.reference}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("don")}</dt><dd className="text-dark">{formatPrice(don.montant)}</dd></div>
          <div className="flex justify-between gap-3">
            <dt className="text-gray-600">{t("frais")}</dt>
            <dd className="text-dark">{formatPrice(don.frais)} ({don.couvre_frais ? t("ajoutes") : t("deduits")})</dd>
          </div>
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("debite")}</dt><dd className="font-bold text-dark">{formatPrice(don.total)}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-gray-600">{t("reverse")}</dt><dd className="font-bold text-primary">{formatPrice(don.montant_ong)}</dd></div>
        </dl>

        {don.statut === "paye" && don.date_reversement && (
          <p className="flex gap-2 mt-4 text-sm text-gray-600">
            <CalendarClock size={16} className="text-primary flex-shrink-0 mt-0.5" />
            {t("calendrier", { date: formatDate(don.date_reversement, { day: "numeric", month: "long", year: "numeric" }) })}
          </p>
        )}

        {don.statut === "paye" && <Documents objet="don" id={don.id} className="justify-center mt-4" />}

        <div className="flex flex-wrap justify-center gap-4 mt-6 text-sm font-bold">
          <Link href="/profil/dons" className="flex items-center gap-1.5 text-primary hover:underline"><CheckCircle size={15} /> {t("mesDons")}</Link>
          <Link href="/give" className="text-primary hover:underline">{t("autres")}</Link>
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense>
      <RetourDon />
    </Suspense>
  );
}
