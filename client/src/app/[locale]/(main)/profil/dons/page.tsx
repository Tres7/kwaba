"use client";

import { Link } from "@/i18n/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle, Clock, FileText, HandHeart } from "lucide-react";
import api from "@/lib/api";
import { useTextesGive } from "@/lib/give";
import { urlExterneSure } from "@/lib/url-sure";
import SubPageHeader from "@/components/layout/SubPageHeader";
import type { Don } from "@/types/api/give";
import Documents from "@/components/documents/Documents";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

interface ReponseDons {
  results: Don[];
  total_donne: number;
  nb_payes: number;
}

function Suivi({ don }: { don: Don }) {
  const { formatDate } = useFormat();
  const t = useTranslations("mesDons");
  if (don.statut === "en_attente") return <span className="flex items-center gap-1 text-amber-700"><Clock size={13} /> {t("enAttente")}</span>;
  if (don.reversement?.statut === "effectue") {
    return (
      <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-secondary">
        <span className="flex items-center gap-1"><CheckCircle size={13} /> {t("reverseLe", { date: formatDate(don.reversement.effectue_le ?? "") })}</span>
        {urlExterneSure(don.reversement.justificatif) && (
          <a href={urlExterneSure(don.reversement.justificatif)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 font-bold text-primary hover:underline">
            <FileText size={13} /> {t("preuve")}<span className="sr-only"> {t("preuveSr")}</span>
          </a>
        )}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-gray-600">
      <CheckCircle size={13} className="text-secondary" /> {t("paye", { date: formatDate(don.date_reversement ?? "") })}
    </span>
  );
}

export default function MesDonsPage() {
  const { formatDate, formatPrice } = useFormat();
  const { CAUSES } = useTextesGive();
  const t = useTranslations("mesDons");
  const { data, isLoading } = useQuery({
    queryKey: ["give", "dons"],
    queryFn: async () => (await api.get<ReponseDons>("/v1/give/dons/")).data,
  });

  return (
    <div className="bg-light min-h-[70vh] pb-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        <SubPageHeader title={t("titre")} />
        {data && data.nb_payes > 0 && (
          <div className="bg-primary text-white rounded-2xl p-5 flex items-center gap-4">
            <HandHeart size={28} className="text-accent flex-shrink-0" />
            <p>{t.rich("total", { montant: formatPrice(data.total_donne), nombre: data.nb_payes, strong: (x) => <strong>{x}</strong> })}</p>
          </div>
        )}
        {isLoading ? (
          [0, 1].map((i) => <div key={i} className="h-24 skeleton rounded-2xl" />)
        ) : !data?.results.length ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center">
            <p className="text-gray-600">{t("aucun")}</p>
            <Link href="/give" className="inline-block mt-4 bg-secondary text-white font-bold px-5 py-2.5 rounded-xl">{t("decouvrir")}</Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {data.results.map((don) => {
              const cause = CAUSES[don.organisation.cause];
              return (
                <li key={don.id} className="bg-white rounded-2xl border border-gray-100 p-4 flex gap-4">
                  <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${cause.couleur}`}><cause.icon size={18} /></span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap justify-between gap-2">
                      <Link href={`/give/${don.organisation.slug}`} className="font-bold text-dark hover:text-primary">{don.organisation.nom}</Link>
                      <span className="font-bold text-dark">{formatPrice(don.montant)}</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {don.reference} · {formatDate(don.paye_le ?? don.cree_le)}{don.projet && <> · {don.projet.titre}</>} · {formatPrice(don.montant_ong)} {t("pourOng")}
                    </p>
                    <div className="text-xs mt-2"><Suivi don={don} /></div>
                    {don.statut === "paye" && <Documents objet="don" id={don.id} className="mt-3" />}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
