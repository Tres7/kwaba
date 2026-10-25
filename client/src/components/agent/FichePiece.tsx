"use client";

import { useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, FileText, Mail, Phone, XCircle } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ouvrirPiece } from "./documents";

export interface Piece {
  type_libelle: string;
  soumise_le: string;
  nb_annonces: number | null;
  hote: { id: string; nom: string; email: string; telephone: string | null; inscrit_le: string };
}

/** Contrôle à distance d'une pièce d'identité : lisible, valide, au nom de l'hôte. Le document est supprimé ensuite. */
export default function FichePiece({ piece, peutDecider, onTerminee }: {
  piece: Piece;
  peutDecider: boolean;
  onTerminee: (message: string) => void;
}) {
  const [refus, setRefus] = useState(false);
  const [motif, setMotif] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const decider = async (decision: "verifiee" | "refusee") => {
    if (decision === "refusee" && motif.trim().length < 10) {
      toast.error("Expliquez à l'hôte le motif du refus (10 caractères au moins).");
      return;
    }
    setEnvoi(true);
    try {
      await api.post(`/v1/verifications/identites/${piece.hote.id}/decision/`, { decision, motif });
      onTerminee(decision === "verifiee"
        ? "Identité vérifiée : ses logements passent dans les visites à faire."
        : "Refus envoyé à l'hôte, le document est supprimé.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-4">
      <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500">Hôte</h2>
        <p className="font-semibold text-dark">{piece.hote.nom}</p>
        <p className="flex flex-col gap-1 text-sm text-gray-600">
          <span className="flex items-center gap-1.5 break-all"><Mail size={14} aria-hidden /> {piece.hote.email}</span>
          {piece.hote.telephone && <a href={`tel:${piece.hote.telephone}`} className="flex items-center gap-1.5 text-primary font-semibold"><Phone size={14} aria-hidden /> {piece.hote.telephone}</a>}
          <span>Inscrit le {formatDate(piece.hote.inscrit_le)}{piece.nb_annonces != null ? ` · ${piece.nb_annonces} annonce${piece.nb_annonces > 1 ? "s" : ""}` : ""}</span>
        </p>
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-gray-500">Document</h2>
        <p className="text-sm text-dark">{piece.type_libelle} · envoyé le {formatDate(piece.soumise_le)}</p>
        <button type="button" onClick={() => ouvrirPiece(piece.hote.id)}
          className="w-full flex items-center justify-center gap-2 text-sm font-bold text-primary border border-primary/30 rounded-xl px-4 py-3 hover:bg-primary/5">
          <FileText size={16} aria-hidden /> Voir le document
        </button>
        <p className="text-xs text-gray-500">Vérifiez qu&apos;il est lisible, en cours de validité et au nom de l&apos;hôte. Chaque consultation est enregistrée.</p>
      </section>

      {peutDecider && (refus ? (
        <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 space-y-3">
          <label className="block text-xs font-bold text-dark uppercase tracking-wide" htmlFor="motif-refus">Motif (envoyé à l&apos;hôte)</label>
          <textarea id="motif-refus" value={motif} onChange={(e) => setMotif(e.target.value)} rows={3}
            placeholder="Ex : photo floue, nom illisible, document expiré"
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={() => setRefus(false)} className="py-3 rounded-xl text-sm font-semibold text-gray-600 bg-gray-50">Annuler</button>
            <button type="button" disabled={envoi} onClick={() => decider("refusee")}
              className="flex items-center justify-center gap-2 bg-red-600 text-white font-bold py-3 rounded-xl text-sm disabled:opacity-60">
              <XCircle size={16} aria-hidden /> Refuser
            </button>
          </div>
        </section>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <button type="button" disabled={envoi} onClick={() => setRefus(true)}
            className="py-4 rounded-xl font-bold text-red-700 border border-red-200 bg-white disabled:opacity-60">
            Refuser
          </button>
          <button type="button" disabled={envoi} onClick={() => decider("verifiee")}
            className="flex items-center justify-center gap-2 bg-secondary text-white font-bold py-4 rounded-xl disabled:opacity-60">
            <CheckCircle2 size={18} aria-hidden /> Identité conforme
          </button>
        </div>
      ))}
    </div>
  );
}
