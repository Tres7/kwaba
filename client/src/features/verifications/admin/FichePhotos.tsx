"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { Check, ExternalLink, Trash2 } from "lucide-react";
import Visionneuse from "@/components/ui/Visionneuse";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { deciderPhotos } from "../api";

export interface PhotosAjoutees {
  id: string;
  name: string;
  city: string;
  type_libelle: string;
  hote: { nom: string; email: string };
  /** Added by the host since the visit: online, to check. */
  ajoutees: string[];
  /** Seen by the agent at the visit, for comparison. */
  deja_verifiees: string[];
  legendes: Record<string, string> | null;
}

const PIECES: Record<string, string> = {
  salon: "Salon", cuisine: "Cuisine", salle_a_manger: "Salle à manger", toilettes: "Toilettes", terrasse: "Terrasse",
  balcon: "Balcon", jardin: "Jardin", piscine: "Piscine", salle_de_sport: "Salle de sport", exterieur: "Extérieur",
  entree: "Entrée", vue: "Vue", parking: "Parking", autre: "Autre", piece_principale: "Pièce principale",
};

const VIGNETTE = "group block w-full cursor-zoom-in focus-visible:outline-hidden";
// Focus drawn inside the thumbnail: the rounded frame around it cuts what is outside
const FOCUS_VIGNETTE = "group-focus-visible:outline-solid group-focus-visible:outline-[3px] group-focus-visible:outline-offset-[-3px] group-focus-visible:outline-primary";

function libelle(code: string | undefined) {
  if (!code) return "Sans pièce";
  const numerotee = code.match(/^(chambre|salle_de_bain)_(\d+)$/);
  if (numerotee) return `${numerotee[1] === "chambre" ? "Chambre" : "Salle de bain"} ${numerotee[2]}`;
  return PIECES[code] ?? code;
}

/** Remote check of the photos a host added to a verified listing: they are online, the agent removes the ones that do
 * not fit (another place, contact details shown, misleading picture) and tells the host why. */
export default function FichePhotos({ photos, peutDecider, onTerminee }: {
  photos: PhotosAjoutees;
  peutDecider: boolean;
  onTerminee: (message: string) => void;
}) {
  const [retirer, setRetirer] = useState<string[]>([]);
  const [motif, setMotif] = useState("");
  const [envoi, setEnvoi] = useState(false);
  // Photo open in the full-screen viewer, in the added ones or in those seen at the visit
  const [ouverte, setOuverte] = useState<{ serie: "ajoutees" | "deja_verifiees"; index: number } | null>(null);
  const tVisionneuse = useTranslations("visionneuse");

  const basculer = (url: string) => setRetirer((r) => (r.includes(url) ? r.filter((u) => u !== url) : [...r, url]));

  const valider = async () => {
    if (retirer.length && motif.trim().length < 10) {
      toast.error("Expliquez à l'hôte pourquoi ces photos sont retirées (10 caractères au moins).");
      return;
    }
    setEnvoi(true);
    try {
      await deciderPhotos(photos.id, { retirer, motif });
      onTerminee(retirer.length
        ? `${retirer.length} photo(s) retirée(s), l'hôte est prévenu.`
        : "Photos contrôlées : elles restent en ligne.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-4">
      <section className="bg-background rounded-2xl border border-gray-100 shadow-xs p-4">
        <p className="text-sm text-dark">
          <strong>{photos.hote.nom || photos.hote.email}</strong> a ajouté {photos.ajoutees.length} photo(s) à son annonce, déjà vérifiée.
          Elles sont en ligne : retirez celles qui ne montrent pas ce logement, qui affichent des coordonnées ou qui sont trompeuses.
        </p>
        <a href={`/hebergements/${photos.id}`} target="_blank" rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1.5 text-sm font-bold text-brand hover:underline">
          Voir l&apos;annonce <ExternalLink size={14} aria-hidden />
        </a>
      </section>

      <section className="bg-background rounded-2xl border border-gray-100 shadow-xs p-4">
        <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500">Photos ajoutées</h2>
        <ul className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
          {photos.ajoutees.map((url, i) => {
            const retiree = retirer.includes(url);
            return (
              <li key={url} className={cn("rounded-xl overflow-hidden border", retiree ? "border-red-400" : "border-gray-100")}>
                <button type="button" onClick={() => setOuverte({ serie: "ajoutees", index: i })} className={VIGNETTE}
                  aria-label={tVisionneuse("agrandir", { photo: `${libelle(photos.legendes?.[url])}, photo ${i + 1}` })}>
                  <img src={url} alt="" className={cn("w-full h-32 object-cover", FOCUS_VIGNETTE, retiree && "opacity-40")} />
                </button>
                <div className="flex items-center justify-between gap-2 px-2 py-1.5">
                  <span className="text-xs text-dark truncate">{libelle(photos.legendes?.[url])}</span>
                  <button type="button" disabled={!peutDecider} onClick={() => basculer(url)} aria-pressed={retiree}
                    className={cn("flex items-center gap-1 text-xs font-bold rounded-lg px-2 py-1 disabled:opacity-50",
                      retiree ? "bg-red-50 text-red-700" : "text-gray-600 hover:bg-gray-50")}>
                    <Trash2 size={13} aria-hidden /> {retiree ? "Retirée" : "Retirer"}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      {photos.deja_verifiees.length > 0 && (
        <details className="bg-surface rounded-2xl border border-gray-100 shadow-xs p-4">
          <summary className="text-xs font-bold uppercase tracking-wide text-gray-500 cursor-pointer">
            Photos vues à la visite ({photos.deja_verifiees.length}), pour comparer
          </summary>
          <ul className="mt-3 grid grid-cols-3 sm:grid-cols-5 gap-2">
            {photos.deja_verifiees.map((url, i) => (
              <li key={url}>
                <button type="button" onClick={() => setOuverte({ serie: "deja_verifiees", index: i })} className={VIGNETTE}
                  aria-label={tVisionneuse("agrandir", { photo: `${libelle(photos.legendes?.[url])}, photo ${i + 1}` })}>
                  <img src={url} alt="" className={cn("w-full h-20 object-cover rounded-lg", FOCUS_VIGNETTE)} />
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}

      {ouverte && (
        <Visionneuse photos={photos[ouverte.serie]} depart={ouverte.index} nom={photos.name}
          legende={(url) => libelle(photos.legendes?.[url])} onClose={() => setOuverte(null)}
          // Deciding photo after photo, without closing: the same choice as the "Remove" button of the grid
          action={ouverte.serie === "ajoutees" && peutDecider ? (url) => {
            const retiree = retirer.includes(url);
            return (
              <button type="button" onClick={() => basculer(url)} disabled={envoi} aria-pressed={retiree}
                className={cn("flex items-center gap-1.5 text-sm font-bold rounded-xl px-4 py-2.5 disabled:opacity-50",
                  retiree ? "bg-red-600 text-white" : "bg-white/15 text-white hover:bg-white/25")}>
                <Trash2 size={15} aria-hidden /> {retiree ? "Photo retirée · Annuler" : "Retirer cette photo"}
              </button>
            );
          } : undefined} />
      )}

      {peutDecider && (
        <section className="bg-background rounded-2xl border border-gray-100 shadow-xs p-4 space-y-3">
          {retirer.length > 0 && (
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Motif envoyé à l&apos;hôte</span>
              <textarea value={motif} onChange={(e) => setMotif(e.target.value)} rows={3} maxLength={500}
                placeholder="Par exemple : cette photo montre un autre logement."
                className="mt-1 w-full bg-gray-50 border border-gray-200 rounded-xl p-3 text-base sm:text-sm outline-hidden focus:border-primary/50" />
            </label>
          )}
          <button type="button" onClick={valider} disabled={envoi}
            className={cn("w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-bold disabled:opacity-60",
              retirer.length ? "bg-red-600" : "bg-primary")}>
            {retirer.length ? <><Trash2 size={16} aria-hidden /> Retirer {retirer.length} photo(s) et prévenir l&apos;hôte</>
              : <><Check size={16} aria-hidden /> Les photos conviennent</>}
          </button>
        </section>
      )}
    </div>
  );
}
