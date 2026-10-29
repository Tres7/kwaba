"use client";

import { Link, usePathname } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import IconeKwaba from "@/components/layout/IconeKwaba";
import { useModule } from "@/lib/site";
import { cn } from "@/lib/utils";

/**
 * Access to the Concierge from every page of the site (except the conversation itself and the payments): a button
 * in the bottom right corner, like a chat, so that it never covers a form or a photo. Named on large screens,
 * the logo with an "AI" badge on phones. Raised above the booking bar of the listing pages on phones.
 * Nothing is shown (and no request is sent to the Concierge) while the module is hidden.
 */
export default function BoutonConcierge() {
  const t = useTranslations("concierge");
  const pathname = usePathname();
  const affiche = useModule("concierge");
  if (!affiche || pathname.startsWith("/concierge") || pathname.startsWith("/reservation")) return null;
  const barreReservation = pathname.startsWith("/hebergements/");
  return (
    <aside aria-label="Concierge">
      <Link
        href="/concierge"
        aria-label={`Concierge ${t("ia")}`}
        className={cn(
          "fixed z-40 right-4 sm:right-6 flex items-center gap-2.5 rounded-full bg-white border border-gray-200 p-1.5 sm:pr-5 shadow-card-hover hover:border-primary/40 hover:-translate-y-0.5 transition-all",
          barreReservation ? "bottom-24 lg:bottom-6" : "bottom-[calc(1rem+env(safe-area-inset-bottom))] sm:bottom-6",
        )}
      >
        <span className="relative flex-shrink-0">
          <IconeKwaba taille={44} className="rounded-full" />
          <span aria-hidden className="sm:hidden absolute -top-1 -right-1 rounded-full bg-accent text-dark text-[10px] font-bold leading-none px-1.5 py-1 ring-2 ring-white">
            {t("ia")}
          </span>
        </span>
        <span className="hidden sm:inline text-sm font-bold text-dark whitespace-nowrap">Concierge {t("ia")}</span>
      </Link>
    </aside>
  );
}
