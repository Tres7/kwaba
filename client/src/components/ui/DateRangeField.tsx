"use client";

import { useMemo } from "react";
import { Calendar, X } from "lucide-react";
import DateRangeCalendar from "@/components/calendrier/DateRangeCalendar";
import Floating from "@/components/ui/Floating";
import { usePopover } from "@/lib/usePopover";
import { calculateNights, cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

interface DateRangeFieldProps {
  checkIn: string;
  checkOut: string;
  onChange: (checkIn: string, checkOut: string) => void;
  /** "hero": two columns built into the search bar; "field": two framed fields. */
  variant?: "hero" | "field";
  className?: string;
}

const AUCUNE = new Set<string>();

/** Arrival / departure choice with our calendar (identical on all browsers and phones). */
export default function DateRangeField({ checkIn, checkOut, onChange, variant = "field", className }: DateRangeFieldProps) {
  const { formatDate } = useFormat();
  const t = useTranslations("dates");
  const { open, setOpen, ref, panelRef } = usePopover();
  const nuits = useMemo(() => calculateNights(checkIn, checkOut), [checkIn, checkOut]);

  const choisir = (a: string, d: string) => {
    onChange(a, d);
    if (a && d) setOpen(false);
  };

  const libelle = (v: string) => (v ? formatDate(v, { day: "numeric", month: "short" }) : t("ajouter"));

  const moitie = (titre: string, valeur: string) => (
    <button
      type="button" onClick={() => setOpen(true)} aria-expanded={open} aria-haspopup="dialog"
      className={cn(
        "flex-1 min-w-0 text-left",
        variant === "hero" ? "px-5 py-3 hover:bg-gray-50 md:rounded-full" : "px-4 py-3 hover:bg-gray-50",
      )}
    >
      <span className="block text-[11px] font-bold text-dark uppercase tracking-wide">{titre}</span>
      <span className="flex items-center gap-2 mt-1">
        <Calendar size={16} className="text-primary flex-shrink-0 hidden sm:block" />
        <span className={cn("text-base md:text-sm font-medium truncate", valeur ? "text-dark" : "text-gray-400")}>{libelle(valeur)}</span>
      </span>
    </button>
  );

  return (
    <div ref={ref} className={cn("relative", className)}>
      <div className={cn("flex divide-x divide-gray-100", variant === "field" && "border border-gray-200 rounded-xl bg-white overflow-hidden", open && variant === "field" && "border-primary ring-2 ring-primary/20")}>
        {moitie(t("arrivee"), checkIn)}
        {moitie(t("depart"), checkOut)}
      </div>

      {open && (
        <Floating ref={panelRef} anchor={ref} width={680} sheetOnMobile onClose={() => setOpen(false)} label={t("choisirDates")} className="md:p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="font-heading font-bold text-dark">
              {nuits > 0 ? `${t("nuits", { nombre: nuits })} · ${libelle(checkIn)} → ${libelle(checkOut)}` : t("quandPartez")}
            </p>
            <button type="button" onClick={() => setOpen(false)} aria-label={t("fermer")} className="w-9 h-9 rounded-full hover:bg-gray-100 flex items-center justify-center">
              <X size={18} />
            </button>
          </div>
          <DateRangeCalendar checkIn={checkIn} checkOut={checkOut} onChange={choisir} indisponibles={AUCUNE} count={2} />
        </Floating>
      )}
    </div>
  );
}
