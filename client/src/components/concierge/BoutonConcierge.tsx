"use client";

import { Link, usePathname } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import IconeKwaba from "@/components/layout/IconeKwaba";
import { useModule } from "@/lib/site";

/**
 * Access to the Concierge from every page of the site (except the conversation itself and the payments): the Kwa-Ba
 * logo floats against the right edge of the screen, half way up, and opens as a tab on hover.
 * Nothing is shown (and no request is sent to the Concierge) while the module is hidden.
 */
export default function BoutonConcierge() {
  const t = useTranslations("concierge");
  const pathname = usePathname();
  const affiche = useModule("concierge");
  if (!affiche || pathname.startsWith("/concierge") || pathname.startsWith("/reservation")) return null;
  return (
    <aside aria-label="Concierge">
      <Link
        href="/concierge"
        title={`Concierge ${t("ia")}`}
        aria-label={`Concierge ${t("ia")}`}
        className="group fixed z-40 right-0 top-1/2 -translate-y-1/2 flex items-center gap-2 pl-2 pr-2 py-2 rounded-l-2xl bg-white border border-r-0 border-gray-200 shadow-xl hover:pr-3 transition-all"
      >
        <IconeKwaba taille={40} className="flex-shrink-0" />
        <span className="hidden group-hover:inline group-focus-visible:inline text-sm font-bold text-dark whitespace-nowrap">Concierge {t("ia")}</span>
      </Link>
    </aside>
  );
}
