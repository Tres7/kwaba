"use client";

import { useState } from "react";
import { MapPin } from "lucide-react";
import { useConsentement } from "@/providers/ConsentProvider";
import { useTranslations } from "next-intl";

interface MapEmbedProps {
  lieu: string;
  ville: string;
}

/**
 * Google Maps map loaded only with the visitor's consent:
 * without consent, no request is sent to Google (neither IP address nor cookie).
 */
export default function MapEmbed({ lieu, ville }: MapEmbedProps) {
  const t = useTranslations("carte");
  const { consentement, definir } = useConsentement();
  // "Show once": does not change the global choice
  const [unique, setUnique] = useState(false);
  const autorise = consentement?.contenusTiers || unique;
  const requete = encodeURIComponent(`${lieu} ${ville}`.trim());

  if (autorise) {
    return (
      <iframe
        title={`Carte de la zone du logement : ${lieu ? `${lieu}, ` : ""}${ville}`}
        src={`https://maps.google.com/maps?q=${requete}&z=13&output=embed`}
        className="w-full h-full border-0"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
      />
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center text-center gap-3 p-5 bg-[repeating-linear-gradient(45deg,#f8f5f0,#f8f5f0_12px,#f3efe8_12px,#f3efe8_24px)]">
      <MapPin size={28} className="text-primary" aria-hidden />
      <p className="text-sm text-dark max-w-sm">
        {t.rich("avertissement", { strong: (x) => <strong>{x}</strong> })}
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        <button type="button" onClick={() => setUnique(true)} className="px-4 py-2 rounded-xl bg-dark text-white text-sm font-bold">
          {t("afficher")}
        </button>
        <button type="button" onClick={() => definir(true)} className="px-4 py-2 rounded-xl border border-dark text-dark text-sm font-semibold">
          {t("toujours")}
        </button>
      </div>
    </div>
  );
}
