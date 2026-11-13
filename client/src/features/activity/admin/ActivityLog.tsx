"use client";

import { useEffect, useState } from "react";
import {
  Banknote, Box, CalendarDays, Download, Flag, Home, KeyRound, Search, Shield, ShieldAlert, ToggleLeft, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { activityExportUrl } from "../api";
import { clockTime, fullDate, groupByDay, initials } from "../format";
import { useActivity, useActivityEntry } from "../hooks";
import type { ActivityCategory, ActivityEntry, ActivityFilters, LevelFilter, Period } from "../types";

const STYLES: Record<ActivityCategory, { icon: typeof Home; tone: string }> = {
  connections: { icon: KeyRound, tone: "bg-sky-50 text-sky-700" },
  rights: { icon: Shield, tone: "bg-violet-50 text-violet-700" },
  listings: { icon: Home, tone: "bg-emerald-50 text-emerald-700" },
  agenda: { icon: CalendarDays, tone: "bg-primary/10 text-brand" },
  money: { icon: Banknote, tone: "bg-amber-50 text-amber-700" },
  moderation: { icon: Flag, tone: "bg-red-50 text-red-700" },
  objects: { icon: Box, tone: "bg-gray-100 text-gray-700" },
  modules: { icon: ToggleLeft, tone: "bg-teal-50 text-teal-700" },
};

const PERIODS: [Period, string][] = [["24h", "24 h"], ["7d", "7 jours"], ["30d", "30 jours"]];
const LEVELS: [LevelFilter, string][] = [["sensitive", "Sensibles"], ["important", "Importants"], ["all", "Tout"]];
const EMPTY: ActivityFilters = {
  q: "", period: "7d", level: "important", category: "", actor: "", ip: "", target_kind: "", target_id: "",
};

function useDebounced(value: string, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function Segmented<T extends string>({ options, value, onChange, label }: {
  options: [T, string][]; value: T; onChange: (value: T) => void; label: string;
}) {
  return (
    <div className="inline-flex bg-surface border border-gray-200 rounded-xl p-1" role="tablist" aria-label={label}>
      {options.map(([code, text]) => (
        <button key={code} type="button" role="tab" aria-selected={value === code} onClick={() => onChange(code)}
          className={cn("px-3 py-1.5 rounded-lg text-sm font-semibold whitespace-nowrap",
            value === code ? "bg-primary/10 text-brand" : "text-dark")}>
          {text}
        </button>
      ))}
    </div>
  );
}

function CategoryIcon({ category, size = 16 }: { category: ActivityCategory; size?: number }) {
  const { icon: Icon, tone } = STYLES[category] ?? STYLES.objects;
  return (
    <span className={cn("rounded-xl flex items-center justify-center shrink-0", tone, size > 16 ? "w-11 h-11" : "w-9 h-9")}>
      <Icon size={size} aria-hidden />
    </span>
  );
}

export default function ActivityLog() {
  const [filters, setFilters] = useState<ActivityFilters>(EMPTY);
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const q = useDebounced(text);
  const query = { ...filters, q };
  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } = useActivity(query);

  const first = data?.pages[0];
  const entries = data?.pages.flatMap((page) => page.results) ?? [];
  const groups = groupByDay(entries, new Date());
  const total = first ? Object.values(first.counts).reduce((sum, n) => sum + n, 0) : 0;
  const update = (change: Partial<ActivityFilters>) => { setSelected(null); setFilters({ ...filters, ...change }); };
  const scoped = filters.actor || filters.ip || filters.target_id;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Journal d&apos;activité</h1>
          <p className="text-muted text-sm mt-1">Qui a fait quoi, quand et depuis où sur la plateforme.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="relative">
            <span className="sr-only">Rechercher</span>
            <Search size={16} aria-hidden className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input value={text} onChange={(e) => { setSelected(null); setText(e.target.value); }}
              placeholder="Compte, email ou adresse IP"
              className="w-64 max-w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 bg-surface text-sm" />
          </label>
          <Segmented label="Période" options={PERIODS} value={filters.period} onChange={(period) => update({ period })} />
          <a href={activityExportUrl(query)} aria-label="Exporter en CSV" title="Exporter la recherche en CSV"
            className="w-10 h-10 rounded-xl bg-surface border border-gray-200 flex items-center justify-center text-dark hover:bg-gray-50">
            <Download size={17} aria-hidden />
          </a>
        </div>
      </div>

      {first && first.today.sensitive > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-amber-50 border border-amber-200 px-4 py-3">
          <div className="flex items-start gap-3">
            <span className="w-9 h-9 rounded-xl bg-surface text-amber-700 flex items-center justify-center shrink-0">
              <ShieldAlert size={18} aria-hidden />
            </span>
            <div>
              <p className="font-bold text-dark">
                {first.today.sensitive} événement{first.today.sensitive > 1 ? "s" : ""} sensible{first.today.sensitive > 1 ? "s" : ""} aujourd&apos;hui
                {first.today.blocked > 0 && ` · ${first.today.blocked} compte${first.today.blocked > 1 ? "s" : ""} bloqué${first.today.blocked > 1 ? "s" : ""}`}
              </p>
              <p className="text-sm text-gray-600">Les événements courants (connexions, réservations de visite…) sont masqués par défaut.</p>
            </div>
          </div>
          <button type="button" onClick={() => update({ level: "sensitive", period: "24h", category: "" })}
            className="rounded-xl bg-primary text-white font-bold px-4 py-2.5 text-sm">Voir les sensibles</button>
        </div>
      )}

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Catégories">
        <button type="button" role="tab" aria-selected={!filters.category} onClick={() => update({ category: "" })}
          className={cn("inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border",
            !filters.category ? "bg-primary text-white border-primary" : "bg-surface text-dark border-gray-200")}>
          Toutes <span className="tabular-nums opacity-80">{total}</span>
        </button>
        {first?.categories.map(({ code, label }) => {
          const Icon = STYLES[code]?.icon ?? Box;
          const active = filters.category === code;
          if (!active && !first.counts[code]) return null;
          return (
            <button key={code} type="button" role="tab" aria-selected={active} onClick={() => update({ category: code })}
              className={cn("inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border",
                active ? "bg-primary text-white border-primary" : "bg-surface text-dark border-gray-200")}>
              <Icon size={14} aria-hidden /> {label} <span className="tabular-nums opacity-70">{first.counts[code] ?? 0}</span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Segmented label="Niveau" options={LEVELS} value={filters.level} onChange={(level) => update({ level })} />
        {scoped && (
          <button type="button" onClick={() => update({ actor: "", ip: "", target_kind: "", target_id: "" })}
            className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 text-brand text-sm font-semibold px-3 py-1.5">
            {filters.ip ? `Adresse ${filters.ip}` : filters.actor ? "Un seul compte" : "Un seul objet"} <X size={14} aria-hidden />
          </button>
        )}
      </div>

      {isError && <p className="text-sm text-red-700">Le journal n&apos;a pas pu être chargé.</p>}
      {isLoading && <div className="h-96 skeleton rounded-2xl" />}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-4 items-start">
          <section className="min-w-0 bg-background rounded-2xl border border-gray-100 p-3 sm:p-4">
            {entries.length === 0 && <p className="py-10 text-center text-sm text-muted">Aucun événement pour cette recherche.</p>}
            {groups.map((group) => (
              <div key={group.key} className="mb-4 last:mb-0">
                <p className="px-2 pb-2 text-sm">
                  <span className="font-bold text-dark">{group.title}</span>
                  {group.subtitle && <span className="text-muted"> {group.subtitle}</span>}
                  <span className="text-muted"> · {group.entries.length} événement{group.entries.length > 1 ? "s" : ""}</span>
                </p>
                <ul className="space-y-1">
                  {group.entries.map((entry) => (
                    <EntryRow key={entry.id} entry={entry} active={selected === entry.id} onSelect={() => setSelected(entry.id)} />
                  ))}
                </ul>
              </div>
            ))}
            {hasNextPage && (
              <button type="button" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}
                className="mt-3 w-full rounded-xl border border-gray-200 py-2.5 text-sm font-semibold text-dark disabled:opacity-60">
                {isFetchingNextPage ? "Chargement…" : "Charger les événements plus anciens"}
              </button>
            )}
          </section>
          <EntryPanel id={selected} onClose={() => setSelected(null)}
            onFilter={(change) => { setText(""); update({ ...change, level: "all" }); }} />
        </div>
      )}
    </div>
  );
}

function EntryRow({ entry, active, onSelect }: { entry: ActivityEntry; active: boolean; onSelect: () => void }) {
  const actorName = entry.actor?.name ?? (entry.legacy ? "Ancien format" : "Système");
  return (
    <li>
      <button type="button" onClick={onSelect} aria-pressed={active}
        className={cn("w-full flex items-center gap-3 rounded-xl px-2 py-2 text-left border",
          active ? "border-primary bg-primary/5" : "border-transparent hover:bg-gray-50")}>
        <span className="w-11 shrink-0 text-xs font-semibold text-muted tabular-nums">{clockTime(entry.created_at)}</span>
        <CategoryIcon category={entry.category} />
        <span className="flex-1 min-w-0">
          <span className="flex items-center gap-2">
            <span className="font-semibold text-dark text-sm truncate">{entry.label}</span>
            {entry.level === "sensitive" && (
              <span className="shrink-0 rounded-full bg-amber-100 text-amber-800 text-[11px] font-bold px-2 py-0.5">Sensible</span>
            )}
          </span>
          {entry.summary && <span className="block text-xs text-muted truncate">{entry.summary}</span>}
        </span>
        <span className="hidden sm:flex items-center gap-2 shrink-0 max-w-[40%]">
          <span className="w-7 h-7 rounded-full bg-gray-100 text-[10px] font-bold text-dark flex items-center justify-center">
            {initials(actorName)}
          </span>
          <span className="text-xs text-dark truncate">{actorName}</span>
        </span>
      </button>
    </li>
  );
}

function EntryPanel({ id, onClose, onFilter }: {
  id: number | null; onClose: () => void; onFilter: (change: Partial<ActivityFilters>) => void;
}) {
  const { data: entry, isLoading } = useActivityEntry(id);
  if (!id) {
    return (
      <aside className="hidden lg:block bg-surface rounded-2xl border border-gray-100 p-6 text-sm text-muted">
        Choisissez un événement pour voir le détail.
      </aside>
    );
  }
  const content = isLoading || !entry ? <div className="h-64 skeleton rounded-xl" /> : (
    <>
      <div className="flex items-start gap-3">
        <CategoryIcon category={entry.category} size={20} />
        <div className="min-w-0">
          <p className="text-xs font-semibold text-muted">{entry.category_label}</p>
          <p className="font-heading font-bold text-lg text-dark">{entry.label}</p>
        </div>
      </div>
      {entry.level === "sensitive" && (
        <span className="inline-block mt-3 rounded-full bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-1">Événement sensible</span>
      )}
      {entry.legacy && (
        <span className="inline-block mt-3 ml-1 rounded-full bg-gray-100 text-gray-700 text-xs font-bold px-2.5 py-1">Ancien format</span>
      )}
      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Date</dt>
          <dd className="text-dark first-letter:uppercase">{fullDate(entry.created_at)}</dd>
        </div>
        <div>
          <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Compte</dt>
          <dd className="text-dark">
            {entry.actor ? <>{entry.actor.name}{entry.actor.email !== entry.actor.name && <span className="block text-xs text-muted">{entry.actor.email}</span>}</> : "Système (tâche automatique ou serveur)"}
          </dd>
        </div>
        {entry.target && (
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">{entry.target.kind_label} concerné</dt>
            <dd className="text-dark">{entry.target.label || entry.target.id}</dd>
          </div>
        )}
        <div>
          <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Adresse IP</dt>
          <dd className="text-dark font-mono text-xs">{entry.ip ?? "—"}</dd>
        </div>
        {entry.details.length > 0 && (
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Détails</dt>
            <dd className="mt-1 rounded-xl bg-light p-3 space-y-1">
              {entry.details.map((line, i) => (
                <p key={i} className="text-dark break-words"><span className="text-muted">{line.label} : </span>{line.value}</p>
              ))}
            </dd>
          </div>
        )}
      </dl>
      <div className="mt-4 space-y-2">
        {entry.actor?.id && (
          <button type="button" onClick={() => onFilter({ actor: entry.actor?.id ?? "", ip: "", target_kind: "", target_id: "" })}
            className="w-full rounded-xl border border-gray-200 py-2.5 text-sm font-semibold text-brand">Voir l&apos;activité de ce compte</button>
        )}
        {entry.target && (
          <button type="button" onClick={() => onFilter({ target_kind: entry.target?.kind ?? "", target_id: entry.target?.id ?? "", actor: "", ip: "" })}
            className="w-full rounded-xl border border-gray-200 py-2.5 text-sm font-semibold text-brand">
            Tout ce qui concerne {entry.target.kind === "account" ? "ce compte" : "cet objet"}
          </button>
        )}
        {entry.ip && (
          <button type="button" onClick={() => onFilter({ ip: entry.ip ?? "", actor: "", target_kind: "", target_id: "" })}
            className="w-full rounded-xl border border-gray-200 py-2.5 text-sm font-semibold text-brand">Filtrer sur cette adresse IP</button>
        )}
      </div>
    </>
  );
  return (
    <>
      <aside className="hidden lg:block sticky top-6 bg-surface rounded-2xl border border-gray-100 p-5">{content}</aside>
      <div className="lg:hidden fixed inset-0 z-50 flex items-end bg-black/40" onClick={onClose}>
        <div className="w-full max-h-[85vh] overflow-y-auto rounded-t-3xl bg-surface p-5" onClick={(e) => e.stopPropagation()}>
          <div className="flex justify-end">
            <button type="button" onClick={onClose} aria-label="Fermer" className="w-9 h-9 rounded-full flex items-center justify-center text-dark hover:bg-gray-100">
              <X size={18} />
            </button>
          </div>
          {content}
        </div>
      </div>
    </>
  );
}
