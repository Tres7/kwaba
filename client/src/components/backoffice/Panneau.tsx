"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Back-office edit form: panel on the right on large screens, bottom sheet on mobile. */
export default function Panneau({ ouvert, titre, onFermer, onValider, envoi, libelle = "Enregistrer", children }: {
  ouvert: boolean;
  titre: string;
  onFermer: () => void;
  onValider: () => void;
  envoi?: boolean;
  libelle?: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!ouvert) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !envoi) onFermer(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [ouvert, envoi, onFermer]);

  if (!ouvert) return null;
  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-end sm:items-stretch sm:justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={() => !envoi && onFermer()} aria-hidden />
      <form
        method="post"
        role="dialog" aria-modal="true" aria-labelledby="panneau-titre"
        onSubmit={(e) => { e.preventDefault(); if (!envoi) onValider(); }}
        className="relative w-full sm:max-w-lg max-h-[92dvh] sm:max-h-none bg-white rounded-t-3xl sm:rounded-none flex flex-col shadow-card-hover"
      >
        <div className="flex items-center justify-between gap-3 px-6 py-4 border-b border-gray-100">
          <h2 id="panneau-titre" className="font-heading font-bold text-dark text-lg">{titre}</h2>
          <button type="button" onClick={onFermer} aria-label="Fermer" className="relative zone-tactile p-2 rounded-full hover:bg-gray-50 text-gray-500">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">{children}</div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100">
          <button type="button" onClick={onFermer} disabled={envoi} className="px-5 py-2.5 rounded-xl border border-gray-200 text-sm font-medium">Annuler</button>
          <button type="submit" disabled={envoi} className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary-600 disabled:opacity-50">
            {envoi ? "Enregistrement…" : libelle}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}

const champClasse = "w-full px-3 py-2.5 bg-white border border-gray-200 rounded-xl text-base sm:text-sm text-dark focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";

/** Labelled field with its error below it. */
export function Champ({ label, erreur, aide, children, className }: {
  label: string; erreur?: string; aide?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <label className={cn("block", className)}>
      <span className="block text-xs font-bold text-dark uppercase tracking-wide mb-1.5">{label}</span>
      {children}
      {aide && !erreur && <span className="block text-xs text-gray-500 mt-1">{aide}</span>}
      {erreur && <span role="alert" className="block text-xs text-red-600 mt-1">{erreur}</span>}
    </label>
  );
}

export function Saisie(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(champClasse, props.className)} />;
}

export function Zone(props: React.ComponentProps<"textarea">) {
  return <textarea rows={3} {...props} className={cn(champClasse, "resize-y", props.className)} />;
}

export function Liste({ options, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { options: { value: string; label: string }[] }) {
  return (
    <select {...props} className={cn(champClasse, props.className)}>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

export function Interrupteur({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-4 py-1 cursor-pointer">
      <span className="text-sm font-semibold text-dark">{label}</span>
      <input type="checkbox" className="accent-primary w-5 h-5" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

/** Erreurs DRF ({ champ: [message] }) → { champ: message }. */
export function erreursApi(err: unknown): Record<string, string> {
  const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
  const res: Record<string, string> = {};
  if (data && typeof data === "object") {
    for (const [k, v] of Object.entries(data)) res[k] = Array.isArray(v) ? String(v[0]) : String(v);
  }
  if (!Object.keys(res).length) res.detail = "Enregistrement impossible. Vérifiez votre connexion.";
  return res;
}
