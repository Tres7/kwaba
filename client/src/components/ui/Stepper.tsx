"use client";

import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface StepperProps {
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
  label: string;
  /** Text under the label, e.g. "13 years and over". */
  hint?: string;
  className?: string;
}

/** − / + counter (travellers, bedrooms…), usable with the keyboard and by touch. */
export default function Stepper({ value, onChange, min = 0, max = 99, label, hint, className }: StepperProps) {
  const t = useTranslations("voyageurs");
  const bouton = "relative zone-tactile w-9 h-9 rounded-full border flex items-center justify-center transition-colors disabled:opacity-30 disabled:cursor-not-allowed";
  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      <div>
        <p className="text-sm font-semibold text-dark">{label}</p>
        {hint && <p className="text-xs text-muted">{hint}</p>}
      </div>
      <div className="flex items-center gap-3" role="group" aria-label={label}>
        <button type="button" onClick={() => onChange(Math.max(min, value - 1))} disabled={value <= min}
          aria-label={`${t("moins")} : ${label}`} className={cn(bouton, "border-gray-300 text-dark hover:border-dark")}>
          <Minus size={15} />
        </button>
        <span className="w-6 text-center font-semibold text-dark tabular-nums" aria-live="polite">{value}</span>
        <button type="button" onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max}
          aria-label={`${t("plus")} : ${label}`} className={cn(bouton, "border-gray-300 text-dark hover:border-dark")}>
          <Plus size={15} />
        </button>
      </div>
    </div>
  );
}
