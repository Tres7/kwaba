"use client";

import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Check, Globe } from "lucide-react";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing, type Langue } from "@/i18n/routing";
import { cn, type Devise } from "@/lib/utils";
import SubPageHeader from "@/components/layout/SubPageHeader";
import { useDevise } from "@/components/layout/Devise";

const LANGUES: { code: Langue; nom: string }[] = [
  { code: "fr", nom: "Français" },
  { code: "en", nom: "English" },
];

// Same choice as the FCFA / € switch of the navigation bar (display only, payment in FCFA)
const DEVISES: { valeur: Devise; nom: string; texte: string }[] = [
  { valeur: "XOF", nom: "fcfa", texte: "fcfaTexte" },
  { valeur: "EUR", nom: "euro", texte: "euroTexte" },
];

export default function LanguagePage() {
  const t = useTranslations("langue");
  const locale = useLocale() as Langue;
  const router = useRouter();
  const pathname = usePathname();
  const [enCours, demarrer] = useTransition();
  const { devise, choisir: choisirDevise } = useDevise();

  const choisir = (langue: Langue) => {
    if (langue !== locale) demarrer(() => router.replace(pathname, { locale: langue }));
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <SubPageHeader title={t("titre")} subtitle={t("sousTitre")} />

      <div className="bg-white rounded-3xl shadow-card p-5 sm:p-8 space-y-8">
        <section>
          <h2 className="font-heading font-semibold text-lg text-dark mb-4 flex items-center gap-2"><Globe size={18} className="text-primary" /> {t("langue")}</h2>
          <div className={cn("grid sm:grid-cols-2 gap-3", enCours && "opacity-60")} role="radiogroup" aria-label={t("langue")}>
            {LANGUES.filter((l) => routing.locales.includes(l.code)).map(({ code, nom }) => {
              const actif = code === locale;
              return (
                <button key={code} type="button" role="radio" aria-checked={actif} lang={code} onClick={() => choisir(code)}
                  className={cn("flex items-center justify-between p-4 rounded-2xl text-left transition-colors",
                    actif ? "border-2 border-primary bg-primary/5" : "border border-gray-200 hover:border-primary/40")}>
                  <div>
                    <p className="font-bold text-dark">{nom}</p>
                    <p className="text-sm text-muted">{t(`description.${code}`)}</p>
                  </div>
                  {actif && <Check size={18} className="text-primary" />}
                </button>
              );
            })}
          </div>
          <p className="text-sm text-muted mt-3">{t("memorise")}</p>
        </section>

        <section>
          <h2 className="font-heading font-semibold text-lg text-dark mb-4">{t("devise")}</h2>
          <div className="grid sm:grid-cols-2 gap-3" role="radiogroup" aria-label={t("devise")}>
            {DEVISES.map(({ valeur, nom, texte }) => {
              const actif = valeur === devise;
              return (
                <button key={valeur} type="button" role="radio" aria-checked={actif} onClick={() => choisirDevise(valeur)}
                  className={cn("flex items-center justify-between p-4 rounded-2xl text-left transition-colors",
                    actif ? "border-2 border-primary bg-primary/5" : "border border-gray-200 hover:border-primary/40")}>
                  <div>
                    <p className="font-bold text-dark">{t(nom)}</p>
                    <p className="text-sm text-muted">{t(texte)}</p>
                  </div>
                  {actif && <Check size={18} className="text-primary" />}
                </button>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
