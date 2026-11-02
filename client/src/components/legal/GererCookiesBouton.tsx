"use client";

import { useConsentement } from "@/providers/ConsentProvider";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/** Opens the cookie choice panel again (footer, cookie policy). Hidden while there is no choice to make. */
export default function GererCookiesBouton({ className, children }: { className?: string; children?: React.ReactNode }) {
  const { mesureActive, ouvrirPreferences } = useConsentement();
  const t = useTranslations("cookies");
  if (!mesureActive) return null;
  return (
    <button type="button" onClick={ouvrirPreferences} className={cn("text-left", className)}>
      {children ?? t("gerer")}
    </button>
  );
}
