"use client";

import { useTranslations } from "next-intl";
import { libellePiece, photosParPiece } from "./pieces";

/** Every photo of the listing, by room (Bedroom 1, Living room…): nothing for a listing whose photos have no room. */
export default function PhotosParPiece({ photos, legendes, nom }: {
  photos: string[];
  legendes?: Record<string, string> | null;
  nom: string;
}) {
  const t = useTranslations("pieces");
  if (!legendes || !Object.keys(legendes).length) return null;
  return (
    <section className="bg-white rounded-2xl shadow-card p-5 sm:p-6">
      <h2 className="font-heading font-bold text-dark text-xl mb-4">{t("titre")}</h2>
      <div className="space-y-5">
        {photosParPiece(photos, legendes).map(([piece, urls]) => {
          const titre = piece ? libellePiece(piece, t) : t("sansPiece");
          return (
            <div key={piece || "autres"}>
              <h3 className="text-sm font-bold text-dark mb-2">{titre}</h3>
              <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
                {urls.map((url, i) => (
                  <img key={url} src={url} alt={`${nom}, ${titre}${urls.length > 1 ? ` ${i + 1}` : ""}`} loading="lazy"
                    className="h-36 sm:h-44 w-auto max-w-[80%] sm:max-w-[60%] flex-shrink-0 object-cover rounded-xl" />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
