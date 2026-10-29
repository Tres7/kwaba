"use client";

import { ChevronLeft, ChevronRight, Search, SearchX } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Colonne<T> {
  titre: string;
  cellule: (ligne: T) => React.ReactNode;
  className?: string;
  /** Hidden in the mobile card (already shown in the card header for example). */
  masquerMobile?: boolean;
}

interface AdminTableProps<T> {
  colonnes: Colonne<T>[];
  lignes: T[] | undefined;
  cle: (ligne: T) => string;
  /** Header of the mobile card (main title of the row). */
  titreMobile: (ligne: T) => React.ReactNode;
  actions?: (ligne: T) => React.ReactNode;
  chargement?: boolean;
  erreur?: boolean;
  onReessayer?: () => void;
}

/** Table on large screens, stacked cards on mobile. */
export default function AdminTable<T>({ colonnes, lignes, cle, titreMobile, actions, chargement, erreur, onReessayer }: AdminTableProps<T>) {
  if (erreur) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
        <p className="text-dark font-semibold mb-2">Impossible de charger les données.</p>
        {onReessayer && <button onClick={onReessayer} className="text-primary font-bold hover:underline">Réessayer</button>}
      </div>
    );
  }
  if (chargement && !lignes) return <div className="space-y-2">{[0, 1, 2, 3].map((i) => <div key={i} className="h-16 skeleton rounded-2xl" />)}</div>;
  if (!lignes?.length) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center text-muted">
        <SearchX size={28} className="mx-auto mb-2 text-gray-300" />
        Aucun résultat pour ces critères.
      </div>
    );
  }

  return (
    <div className={cn("transition-opacity", chargement && "opacity-60")}>
      <div className="hidden md:block bg-white rounded-2xl border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-gray-100">
              {colonnes.map((c) => <th key={c.titre} className={cn("px-4 py-3 font-semibold", c.className)}>{c.titre}</th>)}
              {actions && <th className="px-4 py-3 font-semibold text-right">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {lignes.map((l) => (
              <tr key={cle(l)} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/60 align-middle">
                {colonnes.map((c) => <td key={c.titre} className={cn("px-4 py-3", c.className)}>{c.cellule(l)}</td>)}
                {actions && <td className="px-4 py-3"><div className="flex justify-end gap-1.5 flex-wrap max-w-[14rem] ml-auto">{actions(l)}</div></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="md:hidden space-y-3">
        {lignes.map((l) => (
          <li key={cle(l)} className="bg-white rounded-2xl border border-gray-100 p-4">
            <div className="font-semibold text-dark">{titreMobile(l)}</div>
            <dl className="mt-3 space-y-1.5 text-sm">
              {colonnes.filter((c) => !c.masquerMobile).map((c) => (
                <div key={c.titre} className="flex justify-between gap-3">
                  <dt className="text-muted">{c.titre}</dt>
                  <dd className="text-right text-dark min-w-0">{c.cellule(l)}</dd>
                </div>
              ))}
            </dl>
            {actions && <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-gray-100">{actions(l)}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Pagination({ page, count, pageSize, onChange }: { page: number; count: number; pageSize: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (count === 0) return null;
  const debut = (page - 1) * pageSize + 1;
  const fin = Math.min(page * pageSize, count);
  return (
    <div className="flex items-center justify-between gap-3 mt-4 text-sm">
      <p className="text-muted">{debut}–{fin} sur {count}</p>
      <div className="flex items-center gap-2">
        <button onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label="Page précédente" className="w-9 h-9 rounded-xl border border-gray-200 bg-white flex items-center justify-center disabled:opacity-40"><ChevronLeft size={16} /></button>
        <span className="text-dark font-medium tabular-nums">{page} / {pages}</span>
        <button onClick={() => onChange(page + 1)} disabled={page >= pages} aria-label="Page suivante" className="w-9 h-9 rounded-xl border border-gray-200 bg-white flex items-center justify-center disabled:opacity-40"><ChevronRight size={16} /></button>
      </div>
    </div>
  );
}

export function SearchInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="relative flex-1 min-w-[12rem]">
      <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
      <input
        type="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder}
        className="w-full h-full min-h-[46px] pl-10 pr-3 border border-gray-200 rounded-xl bg-white text-base sm:text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
    </label>
  );
}

const TONS = {
  vert: "bg-green-100 text-green-700",
  rouge: "bg-red-100 text-red-700",
  orange: "bg-amber-100 text-amber-700",
  bleu: "bg-blue-100 text-blue-700",
  gris: "bg-gray-100 text-gray-600",
} as const;

export function Pill({ ton, children }: { ton: keyof typeof TONS; children: React.ReactNode }) {
  return <span className={cn("inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full whitespace-nowrap", TONS[ton])}>{children}</span>;
}

export function ActionButton({ onClick, children, danger, disabled }: { onClick: () => void; children: React.ReactNode; danger?: boolean; disabled?: boolean }) {
  return (
    <button
      type="button" onClick={onClick} disabled={disabled}
      className={cn("px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors disabled:opacity-40 whitespace-nowrap",
        danger ? "border-red-200 text-red-700 hover:bg-red-50" : "border-gray-200 text-dark hover:bg-gray-50")}
    >
      {children}
    </button>
  );
}
