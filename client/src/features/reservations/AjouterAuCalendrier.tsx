"use client";

import { CalendarPlus } from "lucide-react";
import { getSession } from "next-auth/react";
import { useLocale, useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { lienCalendrier } from "./api";

/**
 * « Add to my calendar » for a paid stay: an .ics file that the iPhone, Android or Outlook offers to add to the
 * calendar, with the address, the landmark and a reminder the day before.
 */
export default function AjouterAuCalendrier({ reservationId, className }: { reservationId: string; className?: string }) {
  const t = useTranslations("mesReservations");
  const lien = lienCalendrier(reservationId, useLocale());
  return (
    <a
      href={lien}
      onClick={async (e) => {
        // The link goes through the site's proxy, which adds the session: an expired one is renewed first
        e.preventDefault();
        await getSession().catch(() => null);
        window.location.assign(lien);
      }}
      className={cn("inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary-50 text-brand text-sm font-semibold hover:bg-primary-100 transition-colors", className)}
    >
      <CalendarPlus size={15} aria-hidden /> {t("ajouterCalendrier")}
    </a>
  );
}
