"use client";

import { useTranslations } from "next-intl";
import { CalendarCheck, CalendarClock } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { useFormat } from "@/lib/format";
import { useMyVisit } from "./hooks";
import { TIMEZONE, hourMinute } from "./time";

export default function VisitBanner() {
  const t = useTranslations("hostVisit");
  const { formatDate } = useFormat();
  const { data } = useMyVisit();
  if (!data || data.listings.length === 0) return null;

  const toBook = data.listings.filter((l) => !l.appointment).length;
  const next = data.listings.map((l) => l.appointment).filter((a) => a !== null)
    .sort((a, b) => a.start.localeCompare(b.start))[0];

  if (toBook > 0) {
    return (
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-amber-50 border border-amber-200 p-4">
        <div className="flex items-start gap-3">
          <CalendarClock size={22} aria-hidden className="text-amber-800 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-dark">{t("bannerToBook", { count: toBook })}</p>
            <p className="text-sm text-gray-600">{t("bannerToBookHelp")}</p>
          </div>
        </div>
        <Link href="/hote/espace/visite" className="rounded-xl bg-secondary text-white font-bold px-4 py-2.5 text-sm">{t("bannerBook")}</Link>
      </div>
    );
  }
  if (!next) return null;
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-primary/5 border border-primary/20 p-4">
      <p className="flex items-center gap-2 font-bold text-dark">
        <CalendarCheck size={20} aria-hidden className="text-brand" />
        {t("bannerBooked", {
          date: formatDate(next.start, { timeZone: TIMEZONE, weekday: "long", day: "numeric", month: "long" }),
          time: hourMinute(next.start),
        })}
      </p>
      <Link href="/hote/espace/visite" className="text-sm font-bold text-brand">{t("bannerSee")}</Link>
    </div>
  );
}
