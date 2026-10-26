"use client";

import { useState } from "react";
import { ChevronDown, Users } from "lucide-react";
import Floating from "@/components/ui/Floating";
import Stepper from "@/components/ui/Stepper";
import { usePopover } from "@/lib/usePopover";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface GuestsFieldProps {
  value: number;
  onChange: (total: number) => void;
  max?: number;
  /** Look of the trigger: "field" (framed field) or "bare" (inside a search bar). */
  variant?: "field" | "bare";
  className?: string;
}


/** Choice of the number of travellers: panel with adults and children, total passed to the parent. */
export default function GuestsField({ value, onChange, max = 16, variant = "field", className }: GuestsFieldProps) {
  const t = useTranslations("voyageurs");
  const { open, setOpen, ref, panelRef } = usePopover();
  // The booking only stores a total: the split is only for input comfort
  const [enfants, setEnfants] = useState(0);
  const adultes = Math.max(1, value - enfants);

  const maj = (a: number, e: number) => {
    setEnfants(e);
    onChange(a + e);
  };

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-haspopup="dialog"
        className={cn(
          "w-full flex items-center gap-2 text-left",
          variant === "field" && "h-full border border-gray-200 rounded-xl px-4 py-3 bg-white hover:border-gray-300",
          open && variant === "field" && "border-primary ring-2 ring-primary/20",
        )}
      >
        <Users size={16} className="text-primary flex-shrink-0" />
        <span className="flex-1 min-w-0 text-base md:text-sm font-medium text-dark truncate">
          {t("voyageurs", { nombre: value })}
        </span>
        <ChevronDown size={16} className={cn("text-gray-400 transition-transform flex-shrink-0", open && "rotate-180")} />
      </button>

      {open && (
        <Floating ref={panelRef} anchor={ref} width={320} align="end" sheetOnMobile onClose={() => setOpen(false)} label={t("nombreVoyageurs")} className="p-5 space-y-5">
          <Stepper label={t("adultes")} hint={t("adultesAide")} value={adultes} min={1} max={max - enfants} onChange={(a) => maj(a, enfants)} />
          <Stepper label={t("enfants")} hint={t("enfantsAide")} value={enfants} min={0} max={max - adultes} onChange={(e) => maj(adultes, e)} />
          <p className="text-xs text-muted">{t("bebes")}{max < 16 ? ` ${t("maximum", { nombre: max })}` : ""}</p>
          <div className="flex justify-end">
            <button type="button" onClick={() => setOpen(false)} className="px-5 py-2 rounded-xl bg-dark text-white text-sm font-bold">{t("valider")}</button>
          </div>
        </Floating>
      )}
    </div>
  );
}
