"use client";

import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import { useConfigPaiement } from "@/features/paiements";
import { useFormat } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Cleaning fee of the chosen type, from the Kwa-Ba scale: shown as soon as the host picks a type, never typed in. */
export default function FraisMenageType({ type, className }: { type?: string | null; className?: string }) {
  const t = useTranslations("annonce");
  const { formatPrice } = useFormat();
  const { data: config } = useConfigPaiement();
  const montant = type ? config?.frais_menage?.[type] : undefined;
  if (montant == null) return null;
  return (
    <p role="status" className={cn("flex items-start gap-2 rounded-2xl bg-primary-50 text-primary px-4 py-3 text-sm", className)}>
      <Sparkles size={16} className="flex-shrink-0 mt-0.5" aria-hidden />
      <span>
        {montant > 0
          ? <><strong>{t("fraisMenage", { montant: formatPrice(montant) })}</strong> {t("fraisMenageAide")}</>
          : t("fraisMenageZero")}
      </span>
    </p>
  );
}
