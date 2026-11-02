"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FilePenLine, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { useFormat } from "@/lib/format";
import { supprimerBrouillon } from "./api";
import { completude, type BrouillonAnnonce } from "./brouillons";
import { clesHebergements } from "./hooks";

/** Host space: listings started and saved as drafts, with how complete each one is. */
export default function BrouillonsHote({ brouillons, onReprendre }: {
  brouillons: BrouillonAnnonce[];
  onReprendre: (brouillon: BrouillonAnnonce) => void;
}) {
  const t = useTranslations("espaceHote.brouillons");
  const tAnnonce = useTranslations("annonce");
  const { formatDate } = useFormat();
  const queryClient = useQueryClient();

  const supprimer = async (b: BrouillonAnnonce) => {
    if (!window.confirm(t("supprimerQuestion", { nom: b.donnees.name || t("sansTitre") }))) return;
    try {
      await supprimerBrouillon(b.id);
      toast.success(t("supprime"));
      queryClient.invalidateQueries({ queryKey: clesHebergements.brouillons });
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  return (
    <section aria-labelledby="brouillons-titre" className="mb-6">
      <h2 id="brouillons-titre" className="font-heading font-bold text-dark text-lg mb-3">{t("titre", { nombre: brouillons.length })}</h2>
      <ul className="space-y-3">
        {brouillons.map((b) => {
          const { pourcentage } = completude(b.donnees);
          return (
            <li key={b.id} className="bg-white rounded-2xl border border-dashed border-gray-300 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex-1 min-w-0">
                <p className="font-heading font-bold text-dark truncate">{b.donnees.name || t("sansTitre")}</p>
                <p className="text-xs text-gray-500 mt-0.5">{t("modifie", { date: formatDate(b.modifie_le) })}</p>
                <div className="mt-2 flex items-center gap-3">
                  <div role="progressbar" aria-label={tAnnonce("completude.avancement", { pourcentage })} aria-valuenow={pourcentage}
                    aria-valuemin={0} aria-valuemax={100} className="flex-1 max-w-xs h-2 rounded-full bg-gray-200 overflow-hidden">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${pourcentage}%` }} />
                  </div>
                  <span className="text-xs font-semibold text-dark">{pourcentage} %</span>
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button type="button" onClick={() => onReprendre(b)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary text-white text-sm font-semibold hover:bg-primary-600">
                  <FilePenLine size={14} aria-hidden /> {t("reprendre")}
                </button>
                <button type="button" onClick={() => supprimer(b)} aria-label={t("supprimer", { nom: b.donnees.name || t("sansTitre") })}
                  className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 text-red-600 hover:bg-red-50">
                  <Trash2 size={16} aria-hidden />
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
