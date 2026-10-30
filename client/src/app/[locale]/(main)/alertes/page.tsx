"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BellOff, BellRing } from "lucide-react";
import { Link } from "@/i18n/navigation";
import api, { apiErrorMessage } from "@/lib/api";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

interface Resume {
  statut: string;
  hebergement: string;
  hebergement_id: string;
  debut: string;
  fin: string;
}

/** Links of the alert emails: /alertes?confirmer=<token> or /alertes?desinscrire=<token>. Nothing happens without a
 *  click: mail scanners that open links must not confirm or stop an alert. */
function Alertes() {
  const { formatDate } = useFormat();
  const t = useTranslations("alerte");
  const params = useSearchParams();
  const jeton = params.get("confirmer") || params.get("desinscrire") || "";
  const action = params.get("confirmer") ? "confirmer" : "desinscrire";
  const [resume, setResume] = useState<Resume | null>(null);
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const valider = async () => {
    setEnvoi(true);
    setErreur("");
    try {
      setResume((await api.post<Resume>(`/v1/hebergements/alertes/${action}/`, { jeton })).data);
    } catch (err) {
      setErreur(apiErrorMessage(err, t("lienInvalide")));
    } finally {
      setEnvoi(false);
    }
  };

  const Icone = action === "confirmer" ? BellRing : BellOff;
  const dates = resume && { debut: formatDate(resume.debut, { day: "numeric", month: "long" }), fin: formatDate(resume.fin, { day: "numeric", month: "long" }) };
  return (
    <div className="max-w-md mx-auto px-4 py-16 text-center">
      <div className="w-14 h-14 mx-auto rounded-full bg-primary/10 text-primary flex items-center justify-center mb-5"><Icone size={26} aria-hidden /></div>
      <h1 className="font-heading font-bold text-2xl text-dark mb-3">{action === "confirmer" ? t("confirmerTitre") : t("desinscrireTitre")}</h1>
      {!jeton ? (
        <p className="text-gray-600">{t("lienInvalide")}</p>
      ) : resume && dates ? (
        <>
          <p className="text-gray-600">
            {resume.statut === "active" ? t("confirmee", { hebergement: resume.hebergement, ...dates })
              : resume.statut === "annulee" ? t("arretee", { hebergement: resume.hebergement, ...dates })
                : t("terminee", { hebergement: resume.hebergement, ...dates })}
          </p>
          <Link href={`/hebergements/${resume.hebergement_id}`} className="inline-block mt-6 text-sm font-semibold text-primary hover:underline">{t("voirLogement")}</Link>
        </>
      ) : (
        <>
          <p className="text-gray-600 mb-6">{action === "confirmer" ? t("confirmerTexte") : t("desinscrireTexte")}</p>
          {erreur && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3 mb-4">{erreur}</p>}
          <button onClick={valider} disabled={envoi} className="px-6 py-3 rounded-xl bg-primary text-white font-bold disabled:opacity-50">
            {envoi ? "..." : action === "confirmer" ? t("confirmerBouton") : t("desinscrireBouton")}
          </button>
        </>
      )}
    </div>
  );
}

export default function AlertesPage() {
  return <Suspense><Alertes /></Suspense>;
}
