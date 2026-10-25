"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Camera, CheckCircle2, FileText, MapPin, Phone, XCircle } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { cn, formatPrice, libelleType } from "@/lib/utils";
import { ouvrirPiece } from "./documents";

export interface Logement {
  id: string;
  name: string;
  type: string;
  city: string;
  location: string;
  description: string;
  price_per_night: number;
  max_guests: number;
  amenities: string[];
  photos: string[];
  modifiee_apres_verification: boolean;
  cree_le: string;
  hote: {
    id: string;
    nom: string;
    email: string;
    telephone: string | null;
    piece: { statut: "absente" | "soumise" | "verifiee" | "refusee"; type_libelle?: string; motif_refus?: string };
  };
}

const PIECE: Record<Logement["hote"]["piece"]["statut"], { libelle: string; classe: string }> = {
  absente: { libelle: "Pièce d'identité pas encore envoyée", classe: "bg-red-50 text-red-700" },
  soumise: { libelle: "Pièce d'identité à contrôler", classe: "bg-amber-50 text-amber-800" },
  verifiee: { libelle: "Identité déjà vérifiée", classe: "bg-green-50 text-green-700" },
  refusee: { libelle: "Pièce d'identité refusée, à renvoyer", classe: "bg-red-50 text-red-700" },
};

/** Visite d'un logement : l'annonce à comparer, la grille de contrôle, les photos prises sur place, la décision. */
export default function FicheLogement({ logement, controlesLibelles, maxPhotos, peutDecider, onTerminee }: {
  logement: Logement;
  controlesLibelles: Record<string, string>;
  maxPhotos: number;
  peutDecider: boolean;
  onTerminee: (message: string) => void;
}) {
  const [controles, setControles] = useState<Record<string, boolean>>({});
  const [commentaire, setCommentaire] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [envoi, setEnvoi] = useState<"validee" | "refusee" | null>(null);

  const toutCoche = Object.keys(controlesLibelles).every((cle) => controles[cle]);
  const piece = PIECE[logement.hote.piece.statut];
  const telephone = logement.hote.telephone?.replace(/[^\d+]/g, "");
  const carte = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${logement.location}, ${logement.city}`)}`;

  const decider = async (decision: "validee" | "refusee") => {
    if (decision === "refusee" && commentaire.trim().length < 10) {
      toast.error("Expliquez à l'hôte le motif du refus (10 caractères au moins).");
      return;
    }
    if (decision === "validee" && !window.confirm(`Publier « ${logement.name} » ?`)) return;
    setEnvoi(decision);
    const donnees = new FormData();
    donnees.append("decision", decision);
    donnees.append("controles", JSON.stringify(controles));
    donnees.append("commentaire", commentaire);
    photos.forEach((photo) => donnees.append("photos", photo));
    try {
      await api.post(`/v1/verifications/visites/${logement.id}/decision/`, donnees, { headers: { "Content-Type": "multipart/form-data" } });
      onTerminee(decision === "validee" ? "Annonce publiée, l'hôte est prévenu." : "Refus envoyé à l'hôte.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(null);
    }
  };

  return (
    <div className="space-y-4">
      <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500">Hôte</h2>
        <p className="font-semibold text-dark">{logement.hote.nom} <span className="font-normal text-gray-500 break-all">· {logement.hote.email}</span></p>
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2">
          {telephone && (
            <>
              <a href={`tel:${telephone}`} className="flex items-center justify-center gap-1.5 px-3 py-3 rounded-xl bg-gray-100 text-sm font-semibold text-dark"><Phone size={16} aria-hidden /> Appeler</a>
              <a href={`https://wa.me/${telephone.replace("+", "")}`} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center px-3 py-3 rounded-xl bg-green-50 text-sm font-semibold text-green-700">WhatsApp</a>
            </>
          )}
          <a href={carte} target="_blank" rel="noopener noreferrer" className="col-span-2 flex items-center justify-center gap-1.5 px-3 py-3 rounded-xl bg-primary/10 text-sm font-bold text-primary"><MapPin size={16} aria-hidden /> Itinéraire</a>
        </div>
        <div className={cn("flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-sm", piece.classe)}>
          <span>{piece.libelle}{logement.hote.piece.type_libelle ? ` (${logement.hote.piece.type_libelle})` : ""}</span>
          {logement.hote.piece.statut === "soumise" && (
            <button onClick={() => ouvrirPiece(logement.hote.id)} className="flex items-center gap-1 font-bold underline"><FileText size={15} aria-hidden /> Voir</button>
          )}
        </div>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500">Annonce à comparer au logement</h2>
        <p className="text-sm text-dark">{libelleType(logement.type, "fr")} · {logement.max_guests} voyageurs · {formatPrice(logement.price_per_night)} / nuit</p>
        <p className="text-sm text-gray-600">{logement.location ? `${logement.location}, ` : ""}{logement.city}</p>
        {logement.amenities.length > 0 && <p className="text-sm text-gray-600">Équipements annoncés : {logement.amenities.join(", ")}</p>}
        {logement.description && <p className="text-sm text-gray-600 whitespace-pre-line">{logement.description}</p>}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {/* La couverture figure aussi dans la galerie : chaque photo une seule fois */}
          {Array.from(new Set(logement.photos)).map((url) => (
            <a key={url} href={url} target="_blank" rel="noopener noreferrer" className="flex-shrink-0">
              <img src={url} alt="" className="w-32 h-24 object-cover rounded-lg" />
            </a>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500">Contrôles sur place</h2>
        {Object.entries(controlesLibelles).map(([cle, libelle]) => (
          <label key={cle} className="flex items-start gap-3 bg-gray-50 rounded-xl px-3 py-3.5 text-sm text-dark">
            <input type="checkbox" checked={!!controles[cle]} disabled={!peutDecider}
              onChange={(e) => setControles((c) => ({ ...c, [cle]: e.target.checked }))} className="mt-0.5 w-5 h-5 accent-primary flex-shrink-0" />
            {libelle}
          </label>
        ))}

        <label className="block pt-1">
          <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Photos prises sur place (facultatif, {maxPhotos} au plus)</span>
          <span className="mt-2 flex items-center justify-center gap-2 px-4 py-4 rounded-xl border border-dashed border-gray-300 text-sm font-semibold text-gray-600">
            <Camera size={20} aria-hidden /> {photos.length ? `${photos.length} photo(s) sélectionnée(s)` : "Prendre ou choisir des photos"}
          </span>
          <input type="file" accept="image/*" capture="environment" multiple className="sr-only" disabled={!peutDecider}
            onChange={(e) => setPhotos(Array.from(e.target.files ?? []).slice(0, maxPhotos))} />
        </label>
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Commentaire (obligatoire en cas de refus : il est envoyé à l&apos;hôte)</span>
          <textarea value={commentaire} onChange={(e) => setCommentaire(e.target.value)} rows={3} maxLength={2000} disabled={!peutDecider}
            className="mt-2 w-full px-4 py-3 border border-gray-200 rounded-xl text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            placeholder="Ex. : la piscine annoncée n'existe pas ; les photos montrent un autre logement…" />
        </label>
      </section>

      {peutDecider && (
        <div className="grid grid-cols-2 gap-3">
          <button onClick={() => decider("refusee")} disabled={!!envoi} className="flex items-center justify-center gap-2 py-4 rounded-xl border border-red-200 bg-white text-red-700 font-bold disabled:opacity-50">
            <XCircle size={18} aria-hidden /> {envoi === "refusee" ? "Envoi…" : "Refuser"}
          </button>
          <button onClick={() => decider("validee")} disabled={!!envoi || !toutCoche || logement.hote.piece.statut === "absente" || logement.hote.piece.statut === "refusee"}
            title={toutCoche ? undefined : "Cochez tous les contrôles pour valider"}
            className="flex items-center justify-center gap-2 py-4 rounded-xl bg-primary text-white font-bold disabled:opacity-40">
            <CheckCircle2 size={18} aria-hidden /> {envoi === "validee" ? "Envoi…" : "Valider et publier"}
          </button>
        </div>
      )}
    </div>
  );
}
