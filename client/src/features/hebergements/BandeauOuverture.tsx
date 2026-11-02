"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { InstagramLogoIcon } from "@phosphor-icons/react";
import { X } from "lucide-react";
import { usePrelancement } from "./hooks";

export const INSTAGRAM_URL = "https://www.instagram.com/kwabafrica";
// Hidden for the rest of the browsing session once closed
const CLE_MASQUE = "kwaba_bandeau_ouverture_masque";

/** Thin banner at the top of every page while the site is in pre-launch mode. */
export default function BandeauOuverture() {
  const t = useTranslations("prelancement");
  const prelancement = usePrelancement();
  const [masque, setMasque] = useState(true);

  useEffect(() => {
    try {
      setMasque(window.sessionStorage.getItem(CLE_MASQUE) === "1");
    } catch {
      setMasque(false);
    }
  }, []);

  if (!prelancement || masque) return null;

  const masquer = () => {
    setMasque(true);
    try {
      window.sessionStorage.setItem(CLE_MASQUE, "1");
    } catch { /* storage unavailable: hidden for this page only */ }
  };

  return (
    <aside aria-label={t("bandeau")} className="bg-primary text-white text-xs sm:text-sm">
      <div className="max-w-7xl mx-auto flex items-center gap-2 pl-4 pr-1 sm:px-6 min-h-[40px]">
        <p className="flex-1 min-w-0 py-2 text-center">
          {t("bandeau")}{" "}
          <a href={INSTAGRAM_URL} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-bold underline underline-offset-2 whitespace-nowrap">
            <InstagramLogoIcon size={16} weight="bold" aria-hidden /> Instagram
            <span className="sr-only"> ({t("instagram")})</span>
          </a>
        </p>
        <button type="button" onClick={masquer} aria-label={t("fermerBandeau")}
          className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white/80 hover:text-white hover:bg-white/10">
          <X size={16} aria-hidden />
        </button>
      </div>
    </aside>
  );
}
