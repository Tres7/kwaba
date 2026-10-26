"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { selon } from "@/lib/utils";

export interface Confirmation {
  titre: string;
  message: React.ReactNode;
  libelle: string;
  danger?: boolean;
  /** Asks for a reason (required, at least 5 characters), passed to `action`. */
  motif?: boolean;
  action: (motif: string) => Promise<void>;
}

/** Confirmation window for administration actions (replaces window.confirm). */
export default function ConfirmDialog({ confirmation, onClose }: { confirmation: Confirmation | null; onClose: () => void }) {
  const [motif, setMotif] = useState("");
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    setMotif("");
    setEnvoi(false);
  }, [confirmation]);

  useEffect(() => {
    if (!confirmation) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !envoi) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [confirmation, envoi, onClose]);

  if (!confirmation) return null;
  const motifOk = !confirmation.motif || motif.trim().length >= 5;

  const valider = async () => {
    if (!motifOk || envoi) return;
    setEnvoi(true);
    try {
      await confirmation.action(motif.trim());
      onClose();
    } catch {
      // The action shows the error itself (toast); the window stays open
      setEnvoi(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-6">
      <div className="absolute inset-0 bg-black/40" onClick={() => !envoi && onClose()} aria-hidden />
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-titre" className="relative w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-6 shadow-card-hover">
        <div className="flex gap-4">
          <div className={cn("w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0", confirmation.danger ? "bg-red-50 text-red-700" : "bg-primary/10 text-primary")}>
            <AlertTriangle size={20} />
          </div>
          <div className="min-w-0">
            <h2 id="confirm-titre" className="font-heading font-bold text-dark text-lg">{confirmation.titre}</h2>
            <div className="text-sm text-gray-600 mt-1">{confirmation.message}</div>
          </div>
        </div>

        {confirmation.motif && (
          <div className="mt-5">
            <label htmlFor="confirm-motif" className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">Motif (conservé dans le journal)</label>
            <textarea
              id="confirm-motif" value={motif} onChange={(e) => setMotif(e.target.value)} rows={3} maxLength={500} autoFocus
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-base sm:text-sm outline-none focus:border-primary resize-none"
            />
            {!motifOk && <p className="text-xs text-muted mt-1">5 caractères minimum.</p>}
          </div>
        )}

        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-6">
          <button onClick={onClose} disabled={envoi} className="px-5 py-2.5 rounded-xl border border-gray-200 text-sm font-medium">{selon({ fr: "Annuler", en: "Cancel" })}</button>
          <button
            onClick={valider} disabled={!motifOk || envoi}
            className={cn("px-5 py-2.5 rounded-xl text-sm font-bold text-white disabled:opacity-50", confirmation.danger ? "bg-red-600 hover:bg-red-700" : "bg-primary hover:bg-primary-600")}
          >
            {envoi ? "..." : confirmation.libelle}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
