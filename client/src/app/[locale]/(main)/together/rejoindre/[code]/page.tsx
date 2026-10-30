"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin, Users } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import type { ApercuInvitation } from "@/types/api/voyage";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

export default function RejoindrePage() {
  const { formatDate } = useFormat();
  const t = useTranslations("together");
  const { code } = useParams<{ code: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  const { data: v, isError, error } = useQuery({
    queryKey: ["invitation", code],
    queryFn: async () => (await api.get<ApercuInvitation>(`/v1/voyages/invitations/${code}/`)).data,
    retry: false,
  });

  const rejoindre = async () => {
    setEnvoi(true);
    try {
      const res = await api.post<{ id: string }>(`/v1/voyages/invitations/${code}/`);
      queryClient.invalidateQueries({ queryKey: ["voyages"] });
      router.push(`/together/${res.data.id}`);
    } catch (err) {
      setErreur(apiErrorMessage(err, t("erreurRejoindre")));
      setEnvoi(false);
    }
  };

  return (
    <div className="bg-light min-h-[70vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-card border border-gray-100 p-6 sm:p-8 text-center">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-primary/10 text-primary flex items-center justify-center"><Users size={26} /></div>
        {isError ? (
          <>
            <h1 className="font-heading font-bold text-dark text-xl mt-4">{t("introuvable")}</h1>
            <p className="text-sm text-gray-600 mt-2">{apiErrorMessage(error, t("lienInvalide"))} {t("demanderLien")}</p>
            <Link href="/together" className="inline-block mt-6 text-primary font-bold hover:underline">{t("decouvrir")}</Link>
          </>
        ) : !v ? (
          <div className="h-40 skeleton rounded-2xl mt-4" />
        ) : (
          <>
            <p className="text-sm text-gray-600 mt-4">{t("invite", { nom: v.organisateur })}</p>
            <h1 className="font-heading font-bold text-dark text-2xl mt-1">{v.nom}</h1>
            <p className="flex items-center justify-center gap-1.5 text-sm text-gray-600 mt-2">
              <MapPin size={14} className="text-primary" /> {v.destination}
              {v.date_debut && v.date_fin && <> · {formatDate(v.date_debut)} → {formatDate(v.date_fin)}</>}
            </p>
            <p className="text-sm text-gray-600 mt-1">{t("membresPourLinstant", { nombre: v.nb_membres })}</p>
            {erreur && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3 mt-4">{erreur}</p>}
            {v.deja_membre ? (
              <Link href={`/together/${v.id}`} className="block w-full mt-6 bg-primary text-white font-bold py-3.5 rounded-2xl">{t("ouvrir")}</Link>
            ) : (
              <button onClick={rejoindre} disabled={envoi} className="w-full mt-6 bg-primary text-white font-bold py-3.5 rounded-2xl disabled:opacity-60">
                {envoi ? t("unInstant") : t("rejoindre")}
              </button>
            )}
            <p className="text-xs text-gray-600 mt-4">{t("visibilite")}</p>
          </>
        )}
      </div>
    </div>
  );
}
