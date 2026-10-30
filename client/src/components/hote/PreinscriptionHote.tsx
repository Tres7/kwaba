"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, ScrollText } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import type { Preinscription } from "@/types/api/contrat";
import { useFormat } from "@/lib/format";

interface Props {
  /** The listing form, shown once the pre-registration is accepted (or when none is needed). */
  children: React.ReactNode;
  onCancel: () => void;
}

/**
 * Pre-launch: the host reads and accepts the pre-registration terms before the new listing form. The text comes from
 * the API, which records the acceptance (date, IP address, browser, text version) and refuses a listing without it.
 */
export default function PreinscriptionHote({ children, onCancel }: Props) {
  const { langue } = useFormat();
  const t = useTranslations("preinscription");
  const queryClient = useQueryClient();
  const [cochee, setCochee] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["preinscription", langue()],
    queryFn: async () => (await api.get<Preinscription>("/v1/contrats/preinscription/")).data,
  });

  if (isLoading) {
    return <p className="flex items-center gap-2 text-sm text-gray-500"><Loader2 size={16} className="animate-spin" aria-hidden /> {t("chargement")}</p>;
  }
  // Nothing to accept (or status unknown: the API still refuses a listing without the pre-registration)
  if (!data || !data.requise || data.acceptee) return <>{children}</>;

  const accepter = async () => {
    setErreur("");
    setEnvoi(true);
    try {
      await api.post("/v1/contrats/preinscription/", { accepte: true, version: data.version, langue: data.langue });
      await queryClient.invalidateQueries({ queryKey: ["preinscription"] });
    } catch (err) {
      setErreur(apiErrorMessage(err, t("erreur")));
      // The text changed in the meantime: show the new version to be read again
      queryClient.invalidateQueries({ queryKey: ["preinscription"] });
      setCochee(false);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <section aria-labelledby="preinscription-titre" className="space-y-5">
      <div className="flex items-start gap-3">
        <span className="w-11 h-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><ScrollText size={22} aria-hidden /></span>
        <div>
          <h2 id="preinscription-titre" className="font-heading font-bold text-xl text-dark">{t("titre")}</h2>
          <p className="text-sm text-gray-600 mt-1">{t("intro")}</p>
        </div>
      </div>

      <p className="text-sm text-dark leading-relaxed bg-light border border-gray-100 rounded-2xl p-4 sm:p-5">{data.texte}</p>

      <label htmlFor="preinscription-case" className="flex items-start gap-3 cursor-pointer text-sm text-dark">
        <input id="preinscription-case" type="checkbox" checked={cochee} onChange={(e) => setCochee(e.target.checked)}
          className="mt-0.5 w-5 h-5 flex-shrink-0 rounded border-gray-300 text-primary focus:ring-primary" />
        <span>{t("case")}</span>
      </label>

      {erreur && <p role="alert" className="text-sm text-red-600">{erreur}</p>}

      <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
        <button type="button" onClick={onCancel}
          className="min-h-[48px] px-6 rounded-xl bg-gray-100 text-dark font-bold hover:bg-gray-200">
          {t("annuler")}
        </button>
        <button type="button" onClick={accepter} disabled={!cochee || envoi}
          className="inline-flex items-center justify-center gap-2 min-h-[48px] px-6 rounded-xl bg-primary text-white font-bold hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed">
          {envoi && <Loader2 size={16} className="animate-spin" aria-hidden />} {t("accepter")}
        </button>
      </div>
    </section>
  );
}
