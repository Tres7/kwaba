"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { CONTOUR_FOCUS_PHOTO } from "@/components/ui/visionneuse-photos";
import { libellePiece, photosParPiece } from "./pieces";

/** Every photo of the listing, by room (Bedroom 1, Living room…): nothing for a listing whose photos have no room. */
export default function PhotosParPiece({ photos, legendes, nom, onAgrandir }: {
  photos: string[];
  legendes?: Record<string, string> | null;
  nom: string;
  /** Opens the photo in the full-screen viewer. */
  onAgrandir: (url: string) => void;
}) {
  const t = useTranslations("pieces");
  const tVisionneuse = useTranslations("visionneuse");
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
                {urls.map((url, i) => {
                  const alt = `${nom}, ${titre}${urls.length > 1 ? ` ${i + 1}` : ""}`;
                  return (
                    <button key={url} type="button" onClick={() => onAgrandir(url)} aria-label={tVisionneuse("agrandir", { photo: alt })}
                      className={cn("max-w-[80%] sm:max-w-[60%] shrink-0 rounded-xl", CONTOUR_FOCUS_PHOTO)}>
                      <img src={url} alt={alt} loading="lazy" className="h-36 sm:h-44 w-auto max-w-full object-cover rounded-xl" />
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
