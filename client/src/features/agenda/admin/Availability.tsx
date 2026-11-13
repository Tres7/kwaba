"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowLeft, CalendarPlus, Copy, Plus, RefreshCw, Trash2, X } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { addException, deleteException, regenerateFeed, saveWeek, setDayLimit } from "../api";
import { useAgendaMutation, useAvailability, useFeed } from "../hooks";
import { dayKey, formatDuration } from "../time";
import type { WeeklySlot } from "../types";

const WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
const DATE = new Intl.DateTimeFormat("fr-FR", { timeZone: "UTC", weekday: "short", day: "numeric", month: "short" });
const inputClass = "rounded-xl border border-gray-200 px-3 py-2 text-sm bg-surface";
const cardClass = "rounded-3xl bg-surface shadow-xs p-5 sm:p-6 mt-4";

export default function Availability() {
  const { data, isLoading, isError } = useAvailability();
  const [cities, setCities] = useState<string[]>([]);
  const [slots, setSlots] = useState<WeeklySlot[]>([]);
  const [city, setCity] = useState("");

  useEffect(() => {
    if (data) {
      setCities(data.cities);
      setSlots(data.weekly_slots);
    }
  }, [data]);

  const save = useAgendaMutation(() => saveWeek({ cities, weekly_slots: slots }));

  if (isLoading) return <p className="text-sm text-gray-500">Chargement…</p>;
  if (isError || !data) return <p className="text-sm text-red-700">Vos disponibilités n&apos;ont pas pu être chargées.</p>;

  const addCity = () => {
    const value = city.trim();
    if (value && !cities.some((c) => c.toLowerCase() === value.toLowerCase())) setCities([...cities, value]);
    setCity("");
  };
  const updateSlot = (index: number, change: Partial<WeeklySlot>) =>
    setSlots(slots.map((s, i) => (i === index ? { ...s, ...change } : s)));

  return (
    <div className="max-w-3xl">
      <Link href="/agent/agenda" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand">
        <ArrowLeft size={16} aria-hidden /> Agenda
      </Link>
      <h1 className="font-heading font-bold text-2xl text-dark mt-3">Mes disponibilités</h1>
      <p className="text-sm text-gray-500 mt-1">
        Les hôtes de vos villes réservent leur visite dans ces plages : {formatDuration(data.rules.visit_duration_min)} par visite,
        {" "}{formatDuration(data.rules.margin_min)} d&apos;écart avant la suivante, {data.rules.max_per_day} visites par jour au plus,
        {" "}{data.rules.notice_h} h à l&apos;avance et sur {data.rules.horizon_days} jours. Retirer une plage n&apos;annule jamais un rendez-vous déjà pris.
      </p>

      <form className={cardClass} onSubmit={(e) => {
        e.preventDefault();
        save.mutate(undefined, {
          onSuccess: () => toast.success("Semaine type enregistrée."),
          onError: (err) => toast.error(apiErrorMessage(err, "Enregistrement impossible.")),
        });
      }}>
        <h2 className="font-heading font-bold text-lg text-dark">Villes couvertes</h2>
        <div className="flex flex-wrap gap-2 mt-3">
          {cities.map((c) => (
            <span key={c} className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-brand font-semibold text-sm pl-3 pr-1 py-1">
              {c}
              <button type="button" onClick={() => setCities(cities.filter((x) => x !== c))} aria-label={`Retirer ${c}`}
                className="w-6 h-6 rounded-full flex items-center justify-center hover:bg-primary/10"><X size={14} /></button>
            </span>
          ))}
          <span className="inline-flex gap-1">
            <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Ajouter une ville" aria-label="Ville"
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCity(); } }} className={inputClass} />
            <button type="button" onClick={addCity} aria-label="Ajouter la ville"
              className="w-10 rounded-xl bg-gray-100 flex items-center justify-center text-dark"><Plus size={16} /></button>
          </span>
        </div>

        <h2 className="font-heading font-bold text-lg text-dark mt-6">Semaine type</h2>
        <div className="mt-3 divide-y divide-gray-100">
          {WEEKDAYS.map((label, weekday) => {
            const ofDay = slots.map((s, i) => ({ ...s, index: i })).filter((s) => s.weekday === weekday);
            return (
              <div key={label} className="py-3 flex flex-wrap items-start gap-3">
                <span className="w-24 pt-2 text-sm font-semibold text-dark">{label}</span>
                <div className="flex-1 space-y-2">
                  {ofDay.length === 0 && <p className="pt-2 text-sm text-gray-500">Indisponible</p>}
                  {ofDay.map((s) => (
                    <div key={s.index} className="flex items-center gap-2">
                      <input type="time" value={s.start} onChange={(e) => updateSlot(s.index, { start: e.target.value })}
                        aria-label={`${label}, début`} className={inputClass} required />
                      <span className="text-gray-500">→</span>
                      <input type="time" value={s.end} onChange={(e) => updateSlot(s.index, { end: e.target.value })}
                        aria-label={`${label}, fin`} className={inputClass} required />
                      <button type="button" onClick={() => setSlots(slots.filter((_, i) => i !== s.index))}
                        aria-label={`Retirer la plage du ${label.toLowerCase()}`} className="w-9 h-9 rounded-xl flex items-center justify-center text-gray-500 hover:text-red-700">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={() => setSlots([...slots, { weekday, start: "08:00", end: "12:00" }])}
                  className="inline-flex items-center gap-1 rounded-xl px-3 py-2 text-sm font-semibold text-brand hover:bg-primary/5">
                  <Plus size={16} aria-hidden /> Plage
                </button>
              </div>
            );
          })}
        </div>
        <button type="submit" disabled={save.isPending}
          className="mt-4 rounded-xl bg-primary text-white font-bold px-5 py-3 text-sm disabled:opacity-60">Enregistrer la semaine</button>
      </form>

      <Exceptions exceptions={data.exceptions} />
      <DayLimits limits={data.day_limits} maxPerDay={data.rules.max_per_day} ceiling={data.rules.per_day_ceiling} />
      <Feed />
    </div>
  );
}

function Exceptions({ exceptions }: { exceptions: { id: number; day: string; kind: "block" | "extra"; start: string | null; end: string | null }[] }) {
  const [day, setDay] = useState("");
  const [kind, setKind] = useState<"block" | "extra">("block");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const add = useAgendaMutation(() => addException({ day, kind, ...(start && end ? { start, end } : {}) }));
  const remove = useAgendaMutation((id: number) => deleteException(id));
  const today = dayKey(new Date());

  return (
    <section className={cardClass}>
      <h2 className="font-heading font-bold text-lg text-dark">Exceptions</h2>
      <p className="text-sm text-gray-500 mt-1">Congés, jour bloqué, ou disponibilité en plus de la semaine type.</p>
      <ul className="mt-3 space-y-2">
        {exceptions.filter((e) => e.day >= today).map((e) => (
          <li key={e.id} className="flex items-center justify-between gap-2 rounded-xl bg-light px-3 py-2 text-sm">
            <span>
              <span className="font-semibold text-dark first-letter:uppercase">{DATE.format(new Date(`${e.day}T00:00:00Z`))}</span>
              {" · "}{e.kind === "block" ? "Indisponible" : "Disponible en plus"}
              {e.start && e.end ? ` de ${e.start} à ${e.end}` : " toute la journée"}
            </span>
            <button type="button" onClick={() => remove.mutate(e.id)} aria-label="Supprimer l'exception"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-red-700"><Trash2 size={15} /></button>
          </li>
        ))}
      </ul>
      <form className="flex flex-wrap items-end gap-2 mt-4" onSubmit={(e) => {
        e.preventDefault();
        add.mutate(undefined, {
          onSuccess: () => { setDay(""); setStart(""); setEnd(""); toast.success("Exception ajoutée."); },
          onError: (err) => toast.error(apiErrorMessage(err, "Ajout impossible.")),
        });
      }}>
        <label className="text-xs font-semibold text-gray-500">Date
          <input type="date" value={day} min={today} onChange={(e) => setDay(e.target.value)} required className={`${inputClass} block mt-1`} />
        </label>
        <label className="text-xs font-semibold text-gray-500">Type
          <select value={kind} onChange={(e) => setKind(e.target.value as "block" | "extra")} className={`${inputClass} block mt-1`}>
            <option value="block">Indisponible</option>
            <option value="extra">Disponible en plus</option>
          </select>
        </label>
        <label className="text-xs font-semibold text-gray-500">De
          <input type="time" value={start} onChange={(e) => setStart(e.target.value)} required={kind === "extra"} className={`${inputClass} block mt-1`} />
        </label>
        <label className="text-xs font-semibold text-gray-500">À
          <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} required={kind === "extra" || !!start} className={`${inputClass} block mt-1`} />
        </label>
        <button type="submit" disabled={add.isPending} className="rounded-xl bg-primary text-white font-bold px-4 py-2.5 text-sm disabled:opacity-60">Ajouter</button>
      </form>
      {kind === "block" && <p className="text-xs text-gray-500 mt-2">Sans heures, toute la journée est bloquée.</p>}
    </section>
  );
}

function DayLimits({ limits, maxPerDay, ceiling }: { limits: { day: string; max_visits: number }[]; maxPerDay: number; ceiling: number }) {
  const [day, setDay] = useState("");
  const [count, setCount] = useState(String(maxPerDay + 1));
  const save = useAgendaMutation(({ key, value }: { key: string; value: number | null }) => setDayLimit(key, value));
  const today = dayKey(new Date());

  return (
    <section className={cardClass}>
      <h2 className="font-heading font-bold text-lg text-dark">Visites par jour</h2>
      <p className="text-sm text-gray-500 mt-1">{maxPerDay} visites par jour au plus. Vous pouvez relever cette limite pour une journée précise.</p>
      <ul className="mt-3 space-y-2">
        {limits.filter((l) => l.day >= today).map((l) => (
          <li key={l.day} className="flex items-center justify-between gap-2 rounded-xl bg-light px-3 py-2 text-sm">
            <span><span className="font-semibold text-dark first-letter:uppercase">{DATE.format(new Date(`${l.day}T00:00:00Z`))}</span> · {l.max_visits} visites</span>
            <button type="button" onClick={() => save.mutate({ key: l.day, value: null })} aria-label="Revenir à la limite habituelle"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-red-700"><Trash2 size={15} /></button>
          </li>
        ))}
      </ul>
      <form className="flex flex-wrap items-end gap-2 mt-4" onSubmit={(e) => {
        e.preventDefault();
        save.mutate({ key: day, value: Number(count) }, {
          onSuccess: () => toast.success("Limite enregistrée."),
          onError: (err) => toast.error(apiErrorMessage(err, "Enregistrement impossible.")),
        });
      }}>
        <label className="text-xs font-semibold text-gray-500">Date
          <input type="date" value={day} min={today} onChange={(e) => setDay(e.target.value)} required className={`${inputClass} block mt-1`} />
        </label>
        <label className="text-xs font-semibold text-gray-500">Visites
          <input type="number" value={count} min={1} max={ceiling} onChange={(e) => setCount(e.target.value)} required className={`${inputClass} block mt-1 w-24`} />
        </label>
        <button type="submit" disabled={save.isPending} className="rounded-xl bg-primary text-white font-bold px-4 py-2.5 text-sm disabled:opacity-60">Enregistrer</button>
      </form>
    </section>
  );
}

function Feed() {
  const { data } = useFeed();
  const regenerate = useAgendaMutation(() => regenerateFeed());
  if (!data) return null;
  return (
    <section className={cardClass}>
      <h2 className="flex items-center gap-2 font-heading font-bold text-lg text-dark"><CalendarPlus size={20} aria-hidden /> Mon calendrier de téléphone</h2>
      <p className="text-sm text-gray-500 mt-1">
        Abonnez Google Agenda ou le calendrier de l&apos;iPhone à cette adresse : vos visites y apparaissent avec le nom de l&apos;annonce et la ville.
        Gardez-la pour vous. L&apos;agenda de Kwa-Ba reste la référence : un calendrier abonné se met à jour avec quelques heures de retard.
      </p>
      <div className="flex flex-wrap gap-2 mt-3">
        <input readOnly value={data.url} aria-label="Adresse d'abonnement" className={`${inputClass} flex-1 min-w-0 font-mono text-xs`} />
        <button type="button" onClick={() => navigator.clipboard.writeText(data.url).then(() => toast.success("Adresse copiée."))}
          className="inline-flex items-center gap-1.5 rounded-xl bg-primary text-white font-bold px-4 py-2 text-sm"><Copy size={15} aria-hidden /> Copier</button>
      </div>
      <button type="button" onClick={() => {
        if (window.confirm("L'ancienne adresse cessera de fonctionner. Continuer ?")) {
          regenerate.mutate(undefined, { onSuccess: () => toast.success("Nouvelle adresse créée.") });
        }
      }} className="inline-flex items-center gap-1.5 mt-3 text-sm font-semibold text-red-700">
        <RefreshCw size={15} aria-hidden /> Révoquer et créer une nouvelle adresse
      </button>
    </section>
  );
}
