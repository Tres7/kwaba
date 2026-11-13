"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { CalendarCog, CheckCircle2, ChevronLeft, ChevronRight, Clock, MapPin, Navigation, Phone, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAgents, useAppointment, useAppointments } from "../hooks";
import {
  TIMEZONE, addDays, addMonths, byDay, dayKey, durationMinutes, formatDuration, hourMinute, inTime, itineraryUrl, minutesOfDay,
  minutesUntil, monthGrid, visitStates, weekDays, weekStart, type VisitState,
} from "../time";
import type { Appointment } from "../types";

const LONG_DAY = new Intl.DateTimeFormat("fr-FR", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long" });
const MONTH = new Intl.DateTimeFormat("fr-FR", { timeZone: "UTC", month: "long", year: "numeric" });
const DAY_LETTERS = ["L", "M", "M", "J", "V", "S", "D"];
const DAY_SHORT = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const HOUR_HEIGHT = 56;

const asDate = (key: string) => new Date(`${key}T00:00:00Z`);
const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

function useNow(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, []);
  return now;
}

function weekLabel(start: string): string {
  const end = addDays(start, 6);
  const [startDay, endDay] = [asDate(start), asDate(end)];
  const sameMonth = start.slice(0, 7) === end.slice(0, 7);
  const first = sameMonth ? String(startDay.getUTCDate()) : LONG_DAY.format(startDay).split(" ").slice(1).join(" ");
  return `${first} – ${LONG_DAY.format(endDay).split(" ").slice(1).join(" ")} ${endDay.getUTCFullYear()}`;
}

export default function AgentAgenda() {
  const { data: session } = useSession();
  const isAdmin = session?.user?.role === "admin";
  const now = useNow();
  const today = dayKey(now);
  const [selected, setSelected] = useState(today);
  const [view, setView] = useState<"week" | "month">("week");
  const [agent, setAgent] = useState("");

  const week = weekStart(selected);
  const [rangeStart, rangeEnd] = view === "week"
    ? [week, addDays(week, 6)]
    : (() => { const grid = monthGrid(selected); return [grid[0], grid[41]]; })();
  const { data: appointments = [], isLoading, isError } = useAppointments(rangeStart, rangeEnd, agent);
  const { data: agents } = useAgents(isAdmin);

  const active = appointments.filter((a) => a.status !== "cancelled");
  const states = visitStates(appointments, now);
  const days = byDay(appointments);
  const next = active.find((a) => states[a.id] === "next");
  const showAgent = isAdmin && agent !== "";

  const move = (step: number) => setSelected(view === "week" ? addDays(selected, 7 * step) : addMonths(selected, step));

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-heading font-bold text-3xl text-dark">Agenda</h1>
          <p className="text-sm text-gray-500 mt-1">
            {view === "week" ? <><span className="lg:hidden">{weekLabel(week)}</span>
              <span className="hidden lg:inline">Semaine du {weekLabel(week)}</span></> : capitalize(MONTH.format(asDate(selected)))}
            <span className="hidden lg:inline"> · {active.length} visite{active.length > 1 ? "s" : ""}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden lg:inline-flex bg-surface rounded-xl p-1 shadow-xs" role="tablist" aria-label="Affichage">
            {([["week", "Semaine"], ["month", "Mois"]] as const).map(([code, label]) => (
              <button key={code} type="button" role="tab" aria-selected={view === code} onClick={() => setView(code)}
                className={cn("px-4 py-2 rounded-lg text-sm font-bold", view === code ? "bg-primary text-white" : "text-dark")}>
                {label}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => setSelected(today)}
            className="hidden lg:block px-4 py-2.5 rounded-xl bg-surface shadow-xs text-sm font-bold text-dark">Aujourd&apos;hui</button>
          <button type="button" onClick={() => move(-1)} aria-label="Période précédente"
            className="w-11 h-11 rounded-xl bg-surface shadow-xs flex items-center justify-center text-dark"><ChevronLeft size={20} /></button>
          <button type="button" onClick={() => move(1)} aria-label="Période suivante"
            className="w-11 h-11 rounded-xl bg-surface shadow-xs flex items-center justify-center text-dark"><ChevronRight size={20} /></button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mt-4">
        <Link href="/agent/agenda/disponibilites"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface shadow-xs text-sm font-semibold text-dark">
          <CalendarCog size={16} aria-hidden /> Mes disponibilités
        </Link>
        {isAdmin && (
          <>
            <Link href="/agent/agenda/couverture"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface shadow-xs text-sm font-semibold text-dark">
              <MapPin size={16} aria-hidden /> Couverture par ville
            </Link>
            <label className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface shadow-xs text-sm">
              <Users size={16} aria-hidden className="text-gray-500" />
              <span className="sr-only">Agenda affiché</span>
              <select value={agent} onChange={(e) => setAgent(e.target.value)} className="bg-transparent font-semibold text-dark py-0.5">
                <option value="">Mon agenda</option>
                <option value="all">Tous les agents</option>
                {agents?.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </label>
          </>
        )}
      </div>

      {isError && <p className="mt-6 text-sm text-red-700">L&apos;agenda n&apos;a pas pu être chargé. Réessayez dans un instant.</p>}

      {next && view === "week" && <NextVisitBanner appointment={next} now={now} showAgent={showAgent} />}

      {view === "week" ? (
        <>
          <div className="lg:hidden">
            <DayStrip week={week} selected={selected} today={today} days={days} onSelect={setSelected} />
            <DayList day={selected} today={today} appointments={days[selected] ?? []} states={states} now={now}
              loading={isLoading} showAgent={showAgent} />
          </div>
          <div className="hidden lg:block">
            <WeekGrid week={week} today={today} days={days} states={states} now={now} showAgent={showAgent} />
          </div>
        </>
      ) : (
        <MonthGrid selected={selected} today={today} days={days}
          onSelect={(key) => { setSelected(key); setView("week"); }} />
      )}
    </div>
  );
}

function NextVisitBanner({ appointment, now, showAgent }: { appointment: Appointment; now: Date; showAgent: boolean }) {
  const { data: detail } = useAppointment(appointment.id);
  const minutes = minutesUntil(appointment.start, now);
  return (
    <section className="hidden lg:flex mt-6 items-center justify-between gap-6 rounded-3xl bg-primary text-white px-8 py-6">
      <div className="min-w-0">
        <span className="inline-block rounded-full bg-accent text-night text-sm font-bold px-3 py-1">
          Prochaine visite · {inTime(minutes)}
        </span>
        <Link href={`/agent/agenda/${appointment.id}`} className="block font-heading font-bold text-2xl mt-3 truncate hover:underline">
          {appointment.title} · {appointment.address || appointment.city}
        </Link>
        <p className="flex flex-wrap items-center gap-x-6 gap-y-1 mt-2 text-white/90">
          <span className="inline-flex items-center gap-2"><Clock size={18} aria-hidden /> {hourMinute(appointment.start)} – {hourMinute(appointment.end)}</span>
          <span className="inline-flex items-center gap-2"><MapPin size={18} aria-hidden /> {appointment.city}</span>
          {showAgent && appointment.agent && <span>{appointment.agent.name}</span>}
        </p>
      </div>
      {detail && (
        <a href={itineraryUrl(detail.position, detail.address, detail.city)} target="_blank" rel="noopener noreferrer"
          className="shrink-0 inline-flex items-center gap-2 rounded-2xl bg-white text-primary dark:bg-gray-900 dark:text-primary-800 font-bold px-6 py-4">
          <Navigation size={20} aria-hidden /> Lancer l&apos;itinéraire
        </a>
      )}
    </section>
  );
}

function DayStrip({ week, selected, today, days, onSelect }: {
  week: string; selected: string; today: string; days: Record<string, Appointment[]>; onSelect: (key: string) => void;
}) {
  return (
    <div className="grid grid-cols-7 gap-1.5 mt-5" role="tablist" aria-label="Jours de la semaine">
      {weekDays(week).map((key, i) => {
        const count = (days[key] ?? []).filter((a) => a.status !== "cancelled").length;
        const isSelected = key === selected;
        return (
          <button key={key} type="button" role="tab" aria-selected={isSelected} onClick={() => onSelect(key)}
            aria-label={`${capitalize(LONG_DAY.format(asDate(key)))}, ${count} visite${count > 1 ? "s" : ""}`}
            className={cn("rounded-2xl py-3 flex flex-col items-center gap-1.5 shadow-xs",
              isSelected ? "bg-primary text-white" : "bg-surface text-dark", key === today && !isSelected && "ring-2 ring-primary/30")}>
            <span className={cn("text-xs font-semibold", isSelected ? "text-white/80" : "text-gray-500")}>{DAY_LETTERS[i]}</span>
            <span className="font-heading font-bold text-xl">{asDate(key).getUTCDate()}</span>
            <span className="flex gap-0.5 h-1.5" aria-hidden>
              {Array.from({ length: Math.min(count, 4) }, (_, n) => (
                <span key={n} className={cn("w-1.5 h-1.5 rounded-full", isSelected ? "bg-surface" : "bg-primary")} />
              ))}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function DayList({ day, today, appointments, states, now, loading, showAgent }: {
  day: string; today: string; appointments: Appointment[]; states: Record<string, VisitState>; now: Date;
  loading: boolean; showAgent: boolean;
}) {
  const visits = appointments.filter((a) => a.status !== "cancelled");
  return (
    <section className="mt-6" aria-live="polite">
      <h2 className="font-heading font-bold text-xl text-dark">
        {capitalize(LONG_DAY.format(asDate(day)))}{day === today ? " · aujourd'hui" : ""}
      </h2>
      <p className="text-sm text-gray-500 mt-1">
        {loading ? "Chargement…" : visits.length === 0 ? "Aucune visite"
          : `${visits.length} visite${visits.length > 1 ? "s" : ""} · ${hourMinute(visits[0].start)} → ${hourMinute(visits[visits.length - 1].end)}`}
      </p>
      <ol className="mt-4 space-y-4">
        {appointments.map((a) => (
          <li key={a.id} className="flex gap-3">
            <div className="w-14 shrink-0 pt-3">
              <p className="font-heading font-bold text-dark">{hourMinute(a.start)}</p>
              <p className="text-xs text-gray-500">{formatDuration(durationMinutes(a.start, a.end))}</p>
            </div>
            <VisitCard appointment={a} state={states[a.id]} now={now} showAgent={showAgent} />
          </li>
        ))}
      </ol>
    </section>
  );
}

function StateBadge({ state, appointment, now }: { state: VisitState; appointment: Appointment; now: Date }) {
  if (state === "done") {
    return <span className="inline-flex items-center gap-1 text-sm font-bold text-brand"><CheckCircle2 size={16} aria-hidden /> Terminée</span>;
  }
  if (state === "next") {
    return <span className="inline-block rounded-full bg-accent text-night text-sm font-bold px-3 py-0.5">Prochaine · {inTime(minutesUntil(appointment.start, now))}</span>;
  }
  if (state === "cancelled") return <span className="text-sm font-bold text-red-700">Annulée</span>;
  if (state === "past") return <span className="text-sm font-bold text-amber-800">Décision à rendre</span>;
  return null;
}

function VisitCard({ appointment, state, now, showAgent }: {
  appointment: Appointment; state: VisitState; now: Date; showAgent: boolean;
}) {
  const isNext = state === "next";
  const { data: detail } = useAppointment(isNext ? appointment.id : "");
  return (
    <div className={cn("flex-1 min-w-0 rounded-3xl p-5 shadow-xs",
      isNext ? "bg-primary text-white" : "bg-surface text-dark", state === "cancelled" && "opacity-60")}>
      <Link href={`/agent/agenda/${appointment.id}`} className="block">
        <StateBadge state={state} appointment={appointment} now={now} />
        <p className={cn("font-heading font-bold text-lg truncate", state !== "upcoming" && "mt-1.5", state === "cancelled" && "line-through")}>
          {appointment.title}
        </p>
        <p className={cn("flex items-center gap-1.5 text-sm mt-1", isNext ? "text-white/90" : "text-gray-500")}>
          <MapPin size={15} aria-hidden /> <span className="truncate">{appointment.address || appointment.city}</span>
          {appointment.origin === "phone" && <span className="inline-flex items-center gap-1 ml-2"><Phone size={13} aria-hidden /> par téléphone</span>}
        </p>
        {showAgent && appointment.agent && <p className={cn("text-xs mt-1", isNext ? "text-white/80" : "text-gray-500")}>{appointment.agent.name}</p>}
      </Link>
      {isNext && detail && (
        <a href={itineraryUrl(detail.position, detail.address, detail.city)} target="_blank" rel="noopener noreferrer"
          className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-white text-primary dark:bg-gray-900 dark:text-primary-800 font-bold py-3.5">
          <Navigation size={18} aria-hidden /> Lancer l&apos;itinéraire
        </a>
      )}
    </div>
  );
}

function WeekGrid({ week, today, days, states, now, showAgent }: {
  week: string; today: string; days: Record<string, Appointment[]>; states: Record<string, VisitState>; now: Date;
  showAgent: boolean;
}) {
  const keys = weekDays(week);
  const all = keys.flatMap((k) => days[k] ?? []);
  const firstHour = Math.min(8, ...all.map((a) => Math.floor(minutesOfDay(a.start) / 60)));
  const lastHour = Math.max(18, ...all.map((a) => Math.ceil((minutesOfDay(a.start) + durationMinutes(a.start, a.end)) / 60)));
  const hours = Array.from({ length: lastHour - firstHour + 1 }, (_, i) => firstHour + i);
  const top = (minutes: number) => ((minutes - firstHour * 60) / 60) * HOUR_HEIGHT;
  const nowMinutes = minutesOfDay(now.toISOString());

  return (
    <section className="mt-6 rounded-3xl bg-background shadow-xs p-6" aria-label="Semaine">
      <div className="flex items-center gap-6 text-sm text-dark mb-4 pl-14">
        <span className="inline-flex items-center gap-2"><span className="w-3.5 h-3.5 rounded-sm bg-gray-200" /> Terminée</span>
        <span className="inline-flex items-center gap-2"><span className="w-3.5 h-3.5 rounded-sm bg-primary" /> Prochaine</span>
        <span className="inline-flex items-center gap-2"><span className="w-3.5 h-3.5 rounded-sm border-2 border-primary" /> À venir</span>
      </div>
      <div className="grid grid-cols-[3.5rem_repeat(7,minmax(0,1fr))]">
        <div />
        {keys.map((key, i) => (
          <div key={key} className="text-center pb-3">
            <p className="text-sm text-gray-500">{DAY_SHORT[i]}</p>
            <p className={cn("mx-auto mt-1 w-10 h-10 rounded-full flex items-center justify-center font-heading font-bold text-lg",
              key === today ? "bg-primary text-white" : "text-dark")}>{asDate(key).getUTCDate()}</p>
          </div>
        ))}
        <div className="relative" style={{ height: (hours.length - 1) * HOUR_HEIGHT }}>
          {hours.map((h) => (
            <span key={h} className="absolute right-2 -translate-y-1/2 text-xs text-gray-500" style={{ top: top(h * 60) }}>
              {String(h).padStart(2, "0")}:00
            </span>
          ))}
        </div>
        {keys.map((key) => (
          <div key={key} className={cn("relative border-l border-gray-100", key === today && "bg-primary/5")}
            style={{ height: (hours.length - 1) * HOUR_HEIGHT }}>
            {hours.map((h) => <div key={h} className="absolute inset-x-0 border-t border-gray-100" style={{ top: top(h * 60) }} />)}
            {key === today && nowMinutes >= firstHour * 60 && nowMinutes <= lastHour * 60 && (
              <div className="absolute inset-x-0 z-10 flex items-center" style={{ top: top(nowMinutes) }} aria-hidden>
                <span className="w-2.5 h-2.5 -ml-1 rounded-full bg-secondary" /><span className="flex-1 h-0.5 bg-secondary" />
              </div>
            )}
            {(days[key] ?? []).map((a) => {
              const state = states[a.id];
              const height = Math.max((durationMinutes(a.start, a.end) / 60) * HOUR_HEIGHT - 4, 26);
              return (
                <Link key={a.id} href={`/agent/agenda/${a.id}`} title={`${hourMinute(a.start)} ${a.title} · ${a.city}`}
                  className={cn("absolute inset-x-1 rounded-xl px-2.5 py-1.5 overflow-hidden text-xs leading-tight",
                    state === "next" && "bg-primary text-white",
                    (state === "done" || state === "past") && "bg-gray-200/70 text-dark",
                    state === "upcoming" && "bg-surface border-2 border-primary text-dark",
                    state === "cancelled" && "bg-surface border border-dashed border-gray-300 text-gray-400 line-through")}
                  style={{ top: top(minutesOfDay(a.start)) + 2, height }}>
                  <span className="block font-bold truncate">{hourMinute(a.start)} {a.title}</span>
                  <span className={cn("block truncate", state === "next" ? "text-white/85" : "text-gray-500")}>
                    {showAgent && a.agent ? a.agent.name : a.address || a.city}
                  </span>
                </Link>
              );
            })}
          </div>
        ))}
      </div>
      <p className="sr-only">Heures affichées dans le fuseau {TIMEZONE}.</p>
    </section>
  );
}

function MonthGrid({ selected, today, days, onSelect }: {
  selected: string; today: string; days: Record<string, Appointment[]>; onSelect: (key: string) => void;
}) {
  const month = selected.slice(0, 7);
  return (
    <section className="mt-6 rounded-3xl bg-background shadow-xs p-4 sm:p-6" aria-label="Mois">
      <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-gray-500 mb-2">
        {DAY_SHORT.map((d) => <span key={d}>{d}</span>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {monthGrid(selected).map((key) => {
          const count = (days[key] ?? []).filter((a) => a.status !== "cancelled").length;
          return (
            <button key={key} type="button" onClick={() => onSelect(key)}
              className={cn("aspect-square sm:aspect-auto sm:h-20 rounded-xl p-1.5 flex flex-col items-center sm:items-start text-sm",
                key.slice(0, 7) === month ? "text-dark" : "text-gray-300", key === today ? "bg-primary/10" : "hover:bg-gray-50")}>
              <span className={cn("font-bold", key === today && "text-brand")}>{asDate(key).getUTCDate()}</span>
              {count > 0 && (
                <span className="mt-auto rounded-full bg-primary text-white text-[11px] font-bold px-1.5 sm:px-2 py-0.5">
                  {count}<span className="hidden sm:inline"> visite{count > 1 ? "s" : ""}</span>
                </span>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}
