"use client";

import { addMonths, eachDayOfInterval, endOfMonth, endOfWeek, format, isSameMonth, startOfMonth, startOfWeek } from "date-fns";
import { enGB, fr } from "date-fns/locale";
import { useLocale, useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn, isoDate } from "@/lib/utils";

const JOURS = { fr: ["lu", "ma", "me", "je", "ve", "sa", "di"], en: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"] };

export interface DayRender {
  disabled?: boolean;
  className?: string;
  title?: string;
  content?: React.ReactNode;
}

interface MonthGridProps {
  /** First month displayed (any day of the month). */
  month: Date;
  onMonthChange: (m: Date) => void;
  /** Number of months side by side (2 on large screens for example). */
  count?: number;
  minMonth?: Date;
  maxMonth?: Date;
  renderDay: (iso: string) => DayRender;
  onDayClick: (iso: string) => void;
  onDayHover?: (iso: string | null) => void;
}

/** Generic month grid (Monday first, labels in the page language). */
export default function MonthGrid({ month, onMonthChange, count = 1, minMonth, maxMonth, renderDay, onDayClick, onDayHover }: MonthGridProps) {
  const locale = useLocale();
  const dateLocale = locale === "en" ? enGB : fr;
  const t = useTranslations("dates");
  const mois = Array.from({ length: count }, (_, i) => addMonths(startOfMonth(month), i));
  const peutReculer = !minMonth || startOfMonth(month) > startOfMonth(minMonth);
  const peutAvancer = !maxMonth || addMonths(startOfMonth(month), count - 1) < startOfMonth(maxMonth);

  return (
    <div className="relative">
      <div className="absolute top-0 inset-x-0 flex justify-between pointer-events-none">
        <button type="button" onClick={() => onMonthChange(addMonths(month, -1))} disabled={!peutReculer} aria-label={t("moisPrecedent")}
          className="pointer-events-auto w-9 h-9 rounded-full flex items-center justify-center hover:bg-gray-100 disabled:opacity-30 disabled:hover:bg-transparent">
          <ChevronLeft size={18} />
        </button>
        <button type="button" onClick={() => onMonthChange(addMonths(month, 1))} disabled={!peutAvancer} aria-label={t("moisSuivant")}
          className="pointer-events-auto w-9 h-9 rounded-full flex items-center justify-center hover:bg-gray-100 disabled:opacity-30 disabled:hover:bg-transparent">
          <ChevronRight size={18} />
        </button>
      </div>

      <div className={cn("grid gap-6", count > 1 && "md:grid-cols-2")}>
        {mois.map((m, index) => {
          const jours = eachDayOfInterval({ start: startOfWeek(startOfMonth(m), { weekStartsOn: 1 }), end: endOfWeek(endOfMonth(m), { weekStartsOn: 1 }) });
          return (
            <div key={m.toISOString()} className={cn(index > 0 && "hidden md:block")}>
              <p className="text-center font-heading font-bold text-dark capitalize h-9 leading-9">{format(m, "LLLL yyyy", { locale: dateLocale })}</p>
              <div className="grid grid-cols-7 mt-2 text-center text-[11px] font-semibold text-muted uppercase">
                {JOURS[locale === "en" ? "en" : "fr"].map((j) => <span key={j} className="py-1">{j}</span>)}
              </div>
              <div className="grid grid-cols-7 gap-y-1" onMouseLeave={() => onDayHover?.(null)}>
                {jours.map((d) => {
                  if (!isSameMonth(d, m)) return <span key={d.toISOString()} />;
                  const iso = isoDate(d);
                  const r = renderDay(iso);
                  return (
                    <button
                      key={iso} type="button" disabled={r.disabled} title={r.title}
                      onClick={() => onDayClick(iso)} onMouseEnter={() => onDayHover?.(iso)}
                      aria-label={format(d, "EEEE d MMMM yyyy", { locale: dateLocale }) + (r.title ? `, ${r.title}` : "")}
                      className={cn("h-10 text-sm flex items-center justify-center transition-colors", r.className)}
                    >
                      {r.content ?? d.getDate()}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
