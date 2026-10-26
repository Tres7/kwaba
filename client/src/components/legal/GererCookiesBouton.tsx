"use client";

import { useConsentement } from "@/providers/ConsentProvider";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/** Opens the cookie choice panel again (footer, cookie policy). */
export default function GererCookiesBouton({ className, children }: { className?: string; children?: React.ReactNode }) {
  const { ouvrirPreferences } = useConsentement();
  const t = useTranslations("cookies");
  return (
    <button type="button" onClick={ouvrirPreferences} className={cn("text-left", className)}>
      {children ?? t("gerer")}
    </button>
  );
}
