"use client";

import { createContext, Fragment, useCallback, useContext, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn, definirDevise, formatFcfa, type Devise } from "@/lib/utils";

const CLE = "kwaba_devise";
// Back-office and agents: always in FCFA (actual amounts, payouts, invoices)
const ESPACES_INTERNES = /^\/(backoffice|agent)(\/|$)/;

const Contexte = createContext<{ devise: Devise; choisir: (d: Devise) => void }>({ devise: "XOF", choisir: () => {} });

export const useDevise = () => useContext(Contexte);

/** Display currency of prices (FCFA or euros), remembered on the device. Changing the currency rebuilds the page
 *  content: all prices (formatPrice) are displayed again in the new currency. */
export function DeviseProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [choix, setChoix] = useState<Devise>("XOF");

  useEffect(() => {
    try {
      if (window.localStorage.getItem(CLE) === "EUR") setChoix("EUR");
    } catch { /* stockage indisponible : FCFA */ }
  }, []);

  const choisir = useCallback((d: Devise) => {
    setChoix(d);
    try {
      window.localStorage.setItem(CLE, d);
    } catch { /* the choice applies to the current visit */ }
  }, []);

  const effective: Devise = ESPACES_INTERNES.test(pathname) ? "XOF" : choix;
  // Like the language (SynchroLangue): set during rendering, before the components that display prices
  definirDevise(effective);

  return (
    <Contexte.Provider value={{ devise: effective, choisir }}>
      <Fragment key={effective}>{children}</Fragment>
    </Contexte.Provider>
  );
}

/** FCFA / € switch (next to the language choice). */
export function SelecteurDevise({ className, complet = false }: { className?: string; complet?: boolean }) {
  const t = useTranslations("devise");
  const { devise, choisir } = useDevise();
  const options: { valeur: Devise; court: string; long: string }[] = [
    { valeur: "XOF", court: "FCFA", long: t("fcfa") },
    { valeur: "EUR", court: "€", long: t("euro") },
  ];
  return (
    <div role="group" aria-label={t("choisir")} title={t("indicatif")} className={cn("inline-flex items-center gap-1 rounded-full border border-gray-200 p-0.5", className)}>
      {options.map((o) => (
        <button key={o.valeur} type="button" onClick={() => choisir(o.valeur)} aria-pressed={o.valeur === devise} title={o.long}
          className={cn("rounded-full px-2.5 py-1 text-xs font-bold transition-colors",
            o.valeur === devise ? "bg-primary text-white" : "text-dark hover:text-primary")}>
          {complet ? o.long : o.court}
        </button>
      ))}
    </div>
  );
}

/** Next to the currency selector: euros are only an equivalent, the charge is made in FCFA. */
export function MentionDevise({ className }: { className?: string }) {
  const t = useTranslations("devise");
  return <p className={cn("text-xs text-gray-500", className)}>{t("indicatif")}</p>;
}

/** Under a total displayed in euros: the amount actually charged, in FCFA (Mobile Money and card). */
export function MontantDebite({ montant }: { montant: number }) {
  const t = useTranslations("devise");
  const { devise } = useDevise();
  if (devise === "XOF") return null;
  return (
    <>
      <span className="block text-xs font-medium text-gray-500 mt-0.5">{t("debite", { montant: formatFcfa(montant) })}</span>
      <span className="block text-xs text-gray-500">{t("indicatif")}</span>
    </>
  );
}
