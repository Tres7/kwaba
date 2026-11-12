"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Navigation, Phone, ShieldQuestion } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePlanning } from "../hooks";
import { addDays, dayKey, hourMinute, hoursShown, minutesOfDay, rangeMinutes } from "../time";
import type { AgentPlan, PlanningAppointment } from "../types";

const LONG_DAY = new Intl.DateTimeFormat("fr-FR", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long", year: "numeric" });
const ROW_HEIGHT = "h-16";

function useNowMinutes(): { today: string; minutes: number } {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, []);
  return { today: dayKey(now), minutes: minutesOfDay(now.toISOString()) };
}

export default function AgentPlanning() {
  const { today, minutes: nowMinutes } = useNowMinutes();
  const [day, setDay] = useState(today);
  const [city, setCity] = useState("");
  const { data, isLoading, isError } = usePlanning(day, city);

  const agents = data?.agents ?? [];
  const ranges = agents.flatMap((agent) => [
    ...agent.windows.map((w) => rangeMinutes(w, day)),
    ...agent.appointments.map((a) => rangeMinutes(a, day)),
  ]);
  const [firstHour, lastHour] = hoursShown(ranges);
  const span = (lastHour - firstHour) * 60;
  const left = (minutes: number) => `${((Math.min(Math.max(minutes, firstHour * 60), lastHour * 60) - firstHour * 60) / span) * 100}%`;
  const width = ([start, end]: [number, number]) => {
    const from = Math.max(start, firstHour * 60);
    const to = Math.min(end, lastHour * 60);
    return `${(Math.max(to - from, 0) / span) * 100}%`;
  };
  const hours = Array.from({ length: lastHour - firstHour + 1 }, (_, i) => firstHour + i);
  const totalVisits = agents.reduce((sum, agent) => sum + agent.visits, 0);
  const showNow = day === today && nowMinutes >= firstHour * 60 && nowMinutes <= lastHour * 60;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-heading font-bold text-lg text-dark first-letter:uppercase">
            {LONG_DAY.format(new Date(`${day}T00:00:00Z`))}{day === today ? " · aujourd'hui" : ""}
          </p>
          <p className="text-sm text-muted">
            {data ? `${agents.length} agent${agents.length > 1 ? "s" : ""} · ${totalVisits} visite${totalVisits > 1 ? "s" : ""}` : "…"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="Ville"
            className="px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-semibold text-dark">
            <option value="">Toutes les villes</option>
            {data?.cities.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input type="date" value={day} onChange={(e) => e.target.value && setDay(e.target.value)} aria-label="Jour"
            className="px-3 py-2 rounded-xl border border-gray-200 bg-white text-sm text-dark" />
          <button type="button" onClick={() => setDay(today)}
            className="px-4 py-2.5 rounded-xl bg-white border border-gray-200 text-sm font-bold text-dark">Aujourd&apos;hui</button>
          <button type="button" onClick={() => setDay(addDays(day, -1))} aria-label="Jour précédent"
            className="w-10 h-10 rounded-xl bg-white border border-gray-200 flex items-center justify-center text-dark"><ChevronLeft size={18} /></button>
          <button type="button" onClick={() => setDay(addDays(day, 1))} aria-label="Jour suivant"
            className="w-10 h-10 rounded-xl bg-white border border-gray-200 flex items-center justify-center text-dark"><ChevronRight size={18} /></button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-dark">
        <span className="inline-flex items-center gap-2"><span className="w-4 h-3 rounded-sm bg-primary-100" /> Disponible</span>
        <span className="inline-flex items-center gap-2"><span className="w-4 h-3 rounded-sm bg-[repeating-linear-gradient(45deg,#d1d5db_0,#d1d5db_3px,transparent_3px,transparent_6px)]" /> Indisponible</span>
        <span className="inline-flex items-center gap-2"><span className="w-4 h-3 rounded-sm bg-primary" /> Visite prévue</span>
        <span className="inline-flex items-center gap-2"><span className="w-4 h-3 rounded-sm bg-white border border-gray-400" /> Terminée</span>
        <span className="inline-flex items-center gap-2"><span className="w-4 h-3 rounded-sm border border-dashed border-red-400" /> Annulée</span>
        <span className="inline-flex items-center gap-2"><span className="w-4 h-3 rounded-sm bg-amber-400" /> Contrôle a posteriori</span>
      </div>

      {isError && <p className="text-sm text-red-700">Le planning n&apos;a pas pu être chargé.</p>}
      {isLoading && <div className="h-64 skeleton rounded-2xl" />}
      {data && agents.length === 0 && (
        <p className="rounded-2xl bg-white border border-gray-100 p-6 text-center text-sm text-muted">
          Aucun agent{city ? ` ne couvre ${city}` : " actif"}.
        </p>
      )}

      {agents.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 overflow-x-auto">
          <div className="min-w-[860px]">
            <div className="flex border-b border-gray-100">
              <div className="sticky left-0 z-20 w-40 sm:w-52 shrink-0 bg-white px-4 py-2 text-xs font-semibold text-muted">Agent</div>
              <div className="relative flex-1 h-8">
                {hours.map((h, i) => (
                  <span key={h} style={{ left: left(h * 60) }}
                    className={cn("absolute top-2 text-[11px] text-muted tabular-nums",
                      i === 0 ? "" : i === hours.length - 1 ? "-translate-x-full" : "-translate-x-1/2")}>
                    {String(h).padStart(2, "0")}:00
                  </span>
                ))}
              </div>
            </div>
            {agents.map((agent) => (
              <PlanRow key={agent.id} agent={agent} day={day} hours={hours} left={left} width={width}
                nowLeft={showNow ? left(nowMinutes) : null} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PlanRow({ agent, day, hours, left, width, nowLeft }: {
  agent: AgentPlan; day: string; hours: number[]; left: (minutes: number) => string;
  width: (range: [number, number]) => string; nowLeft: string | null;
}) {
  const full = agent.visits >= agent.max_visits;
  return (
    <div className="flex border-b border-gray-100 last:border-b-0">
      <div className="sticky left-0 z-20 w-40 sm:w-52 shrink-0 bg-white px-4 py-2.5 border-r border-gray-100">
        <p className="text-sm font-semibold text-dark truncate">{agent.name || "Agent sans nom"}</p>
        <p className="text-xs text-muted truncate">{agent.cities.join(", ") || "Aucune ville"}</p>
        <p className={cn("text-xs font-semibold tabular-nums", full ? "text-red-700" : "text-dark")}>
          {agent.visits}/{agent.max_visits} visites
        </p>
      </div>
      <div className={cn("relative flex-1", ROW_HEIGHT)}>
        {hours.map((h) => <span key={h} className="absolute inset-y-0 border-l border-gray-100" style={{ left: left(h * 60) }} />)}
        {agent.windows.map((w) => {
          const range = rangeMinutes(w, day);
          return <span key={`w-${w.start}`} className="absolute inset-y-1.5 rounded-md bg-primary-100"
            style={{ left: left(range[0]), width: width(range) }} title={`Disponible ${hourMinute(w.start)} – ${hourMinute(w.end)}`} />;
        })}
        {agent.blocks.map((b) => {
          const range = rangeMinutes(b, day);
          return <span key={`b-${b.start}`} className="absolute inset-y-1.5 rounded-md bg-[repeating-linear-gradient(45deg,#d1d5db_0,#d1d5db_3px,transparent_3px,transparent_6px)]"
            style={{ left: left(range[0]), width: width(range) }} title="Indisponible" />;
        })}
        {agent.appointments.map((a) => <Visit key={a.id} appointment={a} day={day} left={left} width={width} />)}
        {nowLeft && <span className="absolute inset-y-0 w-0.5 bg-secondary z-10" style={{ left: nowLeft }} aria-hidden />}
      </div>
    </div>
  );
}

function Visit({ appointment, day, left, width }: {
  appointment: PlanningAppointment; day: string; left: (minutes: number) => string; width: (range: [number, number]) => string;
}) {
  const range = rangeMinutes(appointment, day);
  const cancelled = appointment.status === "cancelled";
  const label = `${hourMinute(appointment.start)} – ${hourMinute(appointment.end)} · ${appointment.title} · ${appointment.address ? `${appointment.address}, ` : ""}${appointment.city}`;
  return (
    <Link href={`/agent/agenda/${appointment.id}`} title={label} aria-label={label}
      className={cn("absolute top-2.5 bottom-2.5 rounded-lg px-2 flex items-center gap-1 overflow-hidden text-[11px] font-semibold z-[5]",
        appointment.status === "confirmed" && !appointment.post_check && "bg-primary text-white",
        appointment.status === "confirmed" && appointment.post_check && "bg-amber-400 text-dark",
        appointment.status === "done" && "bg-white border border-gray-400 text-gray-600",
        cancelled && "border border-dashed border-red-400 bg-white/80 text-red-700 line-through",
        appointment.on_the_way_at && appointment.status === "confirmed" && "ring-2 ring-accent")}
      style={{ left: left(range[0]), width: width(range) }}>
      {appointment.on_the_way_at && <Navigation size={11} aria-hidden className="shrink-0" />}
      {appointment.origin === "phone" && <Phone size={11} aria-hidden className="shrink-0" />}
      {appointment.post_check && <ShieldQuestion size={11} aria-hidden className="shrink-0" />}
      <span className="truncate">{hourMinute(appointment.start)} {appointment.title}</span>
    </Link>
  );
}
