"use client";

import { useTranslations } from "next-intl";
import { ArrowRight, Send } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { Motif, TuileFlottante } from "./Decor";

/** End of the wizard: what happens now, so that the wait for the agent's visit is not a surprise. */
export default function AnnonceEnvoyee() {
  const t = useTranslations("assistantHote.envoyee");
  return (
    <div className="relative overflow-hidden min-h-dvh bg-light-muted flex flex-col items-center justify-center gap-6 px-6 py-10 text-center">
      <Motif />
      <TuileFlottante picto={Send} phase={1} className="w-32 h-32 sm:w-40 sm:h-40 mb-2" />
      <div className="relative max-w-md">
        <h1 className="font-heading font-bold text-dark text-3xl">{t("titre")}</h1>
        <p className="text-gray-600 mt-3">{t("texte")}</p>
        <ol className="text-left mt-6 space-y-3">
          {(["identite", "visite", "publication"] as const).map((cle, i) => (
            <li key={cle} className="flex gap-3 text-sm text-dark">
              <span className="w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
              {t(`suite.${cle}`)}
            </li>
          ))}
        </ol>
      </div>
      <Link href="/hote/espace" className="relative inline-flex items-center gap-2 px-7 py-3.5 rounded-2xl bg-primary text-white font-bold shadow-button hover:bg-primary-600">
        {t("espace")} <ArrowRight size={18} aria-hidden />
      </Link>
    </div>
  );
}
