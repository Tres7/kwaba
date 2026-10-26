"use client";

import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing, type Langue } from "@/i18n/routing";
import { cn } from "@/lib/utils";

const NOMS: Record<Langue, string> = { fr: "Français", en: "English" };

/** FR / EN switch staying on the same page (the choice is remembered in the NEXT_LOCALE cookie). */
export default function SelecteurLangue({ className, complet = false }: { className?: string; complet?: boolean }) {
  const locale = useLocale() as Langue;
  const t = useTranslations("langue");
  const pathname = usePathname();
  const router = useRouter();
  const [enCours, demarrer] = useTransition();

  const choisir = (langue: Langue) => {
    if (langue === locale) return;
    // Parameters read on click rather than with useSearchParams: the selector is in the bar and the footer of
    // every page, and useSearchParams would prevent their static generation at build time
    const requete = window.location.search.replace(/^\?/, "");
    demarrer(() => router.replace(requete ? `${pathname}?${requete}` : pathname, { locale: langue, scroll: false }));
  };

  return (
    <div role="group" aria-label={t("choisir")} className={cn("inline-flex items-center gap-1 rounded-full border border-gray-200 p-0.5", enCours && "opacity-60", className)}>
      {!complet && <Globe size={14} className="text-gray-400 ml-1.5" aria-hidden />}
      {routing.locales.map((l) => (
        <button
          key={l}
          type="button"
          lang={l}
          onClick={() => choisir(l)}
          aria-pressed={l === locale}
          title={NOMS[l]}
          className={cn("rounded-full px-2.5 py-1 text-xs font-bold uppercase transition-colors",
            l === locale ? "bg-primary text-white" : "text-dark hover:text-primary")}
        >
          {complet ? NOMS[l] : l}
        </button>
      ))}
    </div>
  );
}
