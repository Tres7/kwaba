"use client";

import { ajouterPhoto, rendrePrincipale, retirerPhoto } from "../api";
import { useEffect, useRef, useState } from "react";
import { ImagePlus, Loader2, Star, Trash2, TriangleAlert, X } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { compressImage } from "@/lib/compressImage";
import { cn } from "@/lib/utils";
import type { PhotoVehicule } from "@/types/api/admin";

export const MAX_PHOTOS_VEHICULE = 10;
const FORMATS = ["image/jpeg", "image/png", "image/webp"];

/** Sends one photo (one request per photo: several at once would exceed the size accepted by the server).
 * Returns all the photos of the category, in order. */
export async function envoyerPhotoVehicule(categorieId: number, fichier: File): Promise<PhotoVehicule[]> {
  const corps = new FormData();
  corps.append("image", await compressImage(fichier));
  return ajouterPhoto(categorieId, corps);
}

export interface FichierEnAttente { cle: string; fichier: File; apercu: string }
type Envoi = { cle: string; apercu: string; erreur?: string };

let sequence = 0;
const cle = () => `v${++sequence}`;
export const liberer = (liste: { apercu: string }[]) => liste.forEach((f) => URL.revokeObjectURL(f.apercu));

/**
 * Photos of a vehicle category. Existing category: each chosen photo is sent right away, the main photo and the
 * removals apply immediately. New category (`categorieId` null): the photos wait in `enAttente` and are sent
 * after it is created (see Categories.tsx).
 */
export default function PhotosVehicule({ categorieId, photos, onPhotos, enAttente, onEnAttente, erreur }: {
  categorieId: number | null;
  photos: PhotoVehicule[];
  onPhotos: (photos: PhotoVehicule[]) => void;
  enAttente: FichierEnAttente[];
  onEnAttente: (fichiers: FichierEnAttente[]) => void;
  erreur?: string;
}) {
  const [envois, setEnvois] = useState<Envoi[]>([]);
  const [avis, setAvis] = useState("");
  const [action, setAction] = useState<number | null>(null);
  const [survol, setSurvol] = useState(false);
  const champ = useRef<HTMLInputElement>(null);
  const total = photos.length + envois.length + enAttente.length;
  const complet = total >= MAX_PHOTOS_VEHICULE;

  // Local previews released when the panel closes
  const envoisCourants = useRef(envois);
  envoisCourants.current = envois;
  useEffect(() => () => liberer(envoisCourants.current), []);

  const ajouter = async (liste: FileList | File[]) => {
    setAvis("");
    const fichiers = Array.from(liste);
    const acceptes = fichiers.filter((f) => FORMATS.includes(f.type)).slice(0, Math.max(0, MAX_PHOTOS_VEHICULE - total));
    if (fichiers.some((f) => !FORMATS.includes(f.type))) setAvis("Formats acceptés : JPEG, PNG ou WebP.");
    else if (acceptes.length < fichiers.length) setAvis(`${MAX_PHOTOS_VEHICULE} photos au maximum par catégorie.`);
    if (!acceptes.length) return;

    const nouveaux = acceptes.map((fichier) => ({ cle: cle(), fichier, apercu: URL.createObjectURL(fichier) }));
    if (categorieId === null) {
      onEnAttente([...enAttente, ...nouveaux]);
      return;
    }
    setEnvois((e) => [...e, ...nouveaux.map(({ cle, apercu }) => ({ cle, apercu }))]);
    // One after the other: more reliable on a slow connection
    for (const n of nouveaux) {
      try {
        onPhotos(await envoyerPhotoVehicule(categorieId, n.fichier));
        URL.revokeObjectURL(n.apercu);
        setEnvois((e) => e.filter((x) => x.cle !== n.cle));
      } catch (err) {
        setEnvois((e) => e.map((x) => (x.cle === n.cle ? { ...x, erreur: apiErrorMessage(err, "Envoi impossible.") } : x)));
      }
    }
  };

  const modifier = async (photo: PhotoVehicule, requete: () => Promise<PhotoVehicule[]>) => {
    setAction(photo.id);
    setAvis("");
    try {
      onPhotos(await requete());
    } catch (err) {
      setAvis(apiErrorMessage(err, "Modification impossible."));
    } finally {
      setAction(null);
    }
  };
  const principale = (p: PhotoVehicule) => modifier(p, () => rendrePrincipale(categorieId as number, p.id));
  const retirer = (p: PhotoVehicule) => {
    if (window.confirm("Retirer cette photo ?")) modifier(p, () => retirerPhoto(categorieId as number, p.id));
  };
  const oublier = (c: string) => {
    const f = [...envois, ...enAttente].find((x) => x.cle === c);
    if (f) URL.revokeObjectURL(f.apercu);
    setEnvois((e) => e.filter((x) => x.cle !== c));
    onEnAttente(enAttente.filter((x) => x.cle !== c));
  };

  const bouton = "w-7 h-7 rounded-full bg-white/90 flex items-center justify-center disabled:opacity-40";
  const vignettes = [
    ...photos.map((p, i) => ({ cle: `p${p.id}`, src: p.url, photo: p, principale: i === 0 })),
    ...enAttente.map((f) => ({ cle: f.cle, src: f.apercu, attente: true })),
    ...envois.map((e) => ({ cle: e.cle, src: e.apercu, envoi: !e.erreur, erreur: e.erreur })),
  ] as { cle: string; src: string; photo?: PhotoVehicule; principale?: boolean; attente?: boolean; envoi?: boolean; erreur?: string }[];

  return (
    <div>
      <div role="button" tabIndex={complet ? -1 : 0} aria-disabled={complet} aria-label="Ajouter des photos"
        onClick={() => !complet && champ.current?.click()}
        onKeyDown={(e) => { if (!complet && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); champ.current?.click(); } }}
        onDragOver={(e) => { e.preventDefault(); setSurvol(true); }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(e) => { e.preventDefault(); setSurvol(false); if (!complet && e.dataTransfer.files.length) ajouter(e.dataTransfer.files); }}
        className={cn("rounded-2xl border-2 border-dashed p-4 text-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
          complet ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-primary/50 hover:bg-primary/5",
          survol ? "border-primary bg-primary/5" : erreur ? "border-red-300 bg-red-50/40" : "border-gray-200 bg-gray-50/60")}>
        <ImagePlus size={24} className="mx-auto text-primary mb-1" aria-hidden />
        <p className="text-sm font-medium text-dark">Glissez vos photos ici ou <span className="text-primary font-bold">parcourez</span></p>
        <p className="text-xs text-muted mt-0.5">{total}/{MAX_PHOTOS_VEHICULE} · plusieurs à la fois possible</p>
        <input ref={champ} type="file" accept={FORMATS.join(",")} multiple className="hidden" onClick={(e) => e.stopPropagation()}
          onChange={(e) => { if (e.target.files) ajouter(e.target.files); e.target.value = ""; }} />
      </div>
      {(avis || erreur) && <p role="alert" className="text-xs text-red-600 mt-2">{avis || erreur}</p>}

      {vignettes.length > 0 && (
        <ul className="grid grid-cols-3 gap-2 mt-3">
          {vignettes.map((v) => (
            <li key={v.cle} className={cn("relative aspect-[4/3] rounded-xl overflow-hidden bg-gray-100", v.principale && "ring-2 ring-primary")}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={v.src} alt="" className={cn("w-full h-full object-cover", (v.attente || v.envoi || v.erreur) && "opacity-60")} />
              {v.principale && (
                <span className="absolute top-1.5 left-1.5 bg-primary text-white text-[10px] font-bold uppercase px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Star size={9} className="fill-white" aria-hidden /> Principale
                </span>
              )}
              {v.attente && <span className="absolute top-1.5 left-1.5 bg-dark/80 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">À l&apos;enregistrement</span>}
              {(v.envoi || action === v.photo?.id) && (
                <span className="absolute inset-0 flex items-center justify-center bg-black/30 text-white"><Loader2 size={18} className="animate-spin" aria-label="Envoi en cours" /></span>
              )}
              {v.erreur && (
                <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-red-900/70 text-white p-1.5 text-center">
                  <TriangleAlert size={16} aria-hidden /><span className="text-[10px] leading-tight">{v.erreur}</span>
                </span>
              )}
              {!v.envoi && (
                <span className="absolute bottom-0 inset-x-0 flex justify-end gap-1 p-1 bg-gradient-to-t from-black/60 to-transparent">
                  {v.photo && !v.principale && (
                    <button type="button" onClick={() => principale(v.photo!)} disabled={action !== null} aria-label="Définir comme photo principale"
                      title="Définir comme photo principale" className={cn(bouton, "text-primary")}><Star size={13} aria-hidden /></button>
                  )}
                  {v.photo ? (
                    <button type="button" onClick={() => retirer(v.photo!)} disabled={action !== null} aria-label="Retirer la photo"
                      className={cn(bouton, "text-red-600")}><Trash2 size={13} aria-hidden /></button>
                  ) : (
                    <button type="button" onClick={() => oublier(v.cle)} aria-label="Ne pas ajouter cette photo"
                      className={cn(bouton, "text-dark")}><X size={13} aria-hidden /></button>
                  )}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
