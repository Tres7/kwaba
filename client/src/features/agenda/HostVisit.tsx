"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ArrowLeft, CalendarCheck, Check, Clock, MapPin, Navigation, Phone } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { apiErrorMessage } from "@/lib/api";
import { useFormat } from "@/lib/format";
import { cn, FALLBACK_IMAGE } from "@/lib/utils";
import { bookVisit, moveVisit } from "./api";
import { useAgendaMutation, useFreeSlots, useMoveSlots, useMyVisit } from "./hooks";
import { TIMEZONE, formatDuration, hourMinute, slotsByDay } from "./time";
import type { HostAppointment, ListingToSchedule } from "./types";

export default function HostVisit() {
  const t = useTranslations("hostVisit");
  const { data, isLoading, isError } = useMyVisit();
  const [selected, setSelected] = useState<string[]>([]);
  const [moving, setMoving] = useState<HostAppointment | null>(null);

  const toBook = useMemo(() => data?.listings.filter((l) => !l.appointment) ?? [], [data]);
  const appointments = useMemo(() => {
    const seen = new Map<string, HostAppointment>();
    for (const listing of data?.listings ?? []) {
      if (listing.appointment) seen.set(listing.appointment.id, listing.appointment);
    }
    return [...seen.values()].sort((a, b) => a.start.localeCompare(b.start));
  }, [data]);

  const rules = data?.rules;
  const chosen = toBook.filter((l) => selected.includes(l.id));
  const city = chosen[0]?.city;

  const toggle = (listing: ListingToSchedule) => {
    setMoving(null);
    setSelected((current) => current.includes(listing.id)
      ? current.filter((id) => id !== listing.id)
      : [...current.filter((id) => toBook.find((l) => l.id === id)?.city === listing.city), listing.id]);
  };

  const groupProblem = chosen.length > 1 && rules
    ? chosen.length > rules.max_listings ? t("maxListings", { max: rules.max_listings })
      : chosen.some((l) => !l.has_position) ? t("groupNeedsPosition") : null
    : null;
  const minutes = rules ? rules.visit_duration_min + Math.max(chosen.length - 1, 0) * rules.extra_listing_min : 60;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link href="/hote/espace" className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
        <ArrowLeft size={16} aria-hidden /> {t("back")}
      </Link>
      <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark mt-3">{t("title")}</h1>
      <p className="text-gray-500 text-sm mt-2">{t("intro")}</p>
      {rules && <p className="text-gray-500 text-sm mt-1">{t("rules", { duration: formatDuration(rules.visit_duration_min), notice: rules.notice_h, days: rules.horizon_days })}</p>}

      {isLoading && <p className="mt-8 text-sm text-gray-500">{t("loading")}</p>}
      {isError && <p className="mt-8 text-sm text-red-700">{t("error")}</p>}
      {data && data.listings.length === 0 && (
        <div className="mt-8 rounded-2xl bg-white border border-gray-100 p-6 text-center">
          <p className="font-bold text-dark">{t("empty")}</p>
          <p className="text-sm text-gray-500 mt-1">{t("emptyHelp")}</p>
        </div>
      )}

      {appointments.length > 0 && (
        <ul className="mt-8 space-y-3">
          {appointments.map((a) => (
            <AppointmentCard key={a.id} appointment={a} onMove={() => { setSelected([]); setMoving(a); }} />
          ))}
        </ul>
      )}

      {moving && <SlotPicker mode="move" appointment={moving} minutes={Math.round((new Date(moving.end).getTime() - new Date(moving.start).getTime()) / 60_000)}
        onDone={() => setMoving(null)} />}

      {toBook.length > 0 && (
        <section className="mt-8">
          <h2 className="font-heading font-bold text-lg text-dark">{t("toBook")}</h2>
          {rules && toBook.length > 1 && (
            <p className="text-sm text-gray-500 mt-1">
              {t("sameSite", { distance: rules.same_site_distance_m, duration: formatDuration(rules.visit_duration_min + rules.extra_listing_min) })}
            </p>
          )}
          <ul className="mt-3 space-y-3">
            {toBook.map((listing) => {
              const isSelected = selected.includes(listing.id);
              const disabled = !!city && listing.city !== city;
              return (
                <li key={listing.id}>
                  <button type="button" onClick={() => toggle(listing)} aria-pressed={isSelected} disabled={disabled}
                    className={cn("w-full flex items-center gap-3 rounded-2xl bg-white border p-3 text-left",
                      isSelected ? "border-primary ring-2 ring-primary/20" : "border-gray-100", disabled && "opacity-50")}>
                    <img src={listing.image_url || FALLBACK_IMAGE} alt="" className="w-16 h-16 rounded-xl object-cover bg-gray-100 shrink-0" />
                    <span className="flex-1 min-w-0">
                      <span className="block font-bold text-dark truncate">{listing.name}</span>
                      <span className="flex items-center gap-1 text-sm text-gray-500 truncate"><MapPin size={14} aria-hidden /> {listing.address ? `${listing.address}, ` : ""}{listing.city}</span>
                    </span>
                    <span className={cn("w-7 h-7 rounded-full border-2 flex items-center justify-center shrink-0",
                      isSelected ? "bg-primary border-primary text-white" : "border-gray-300")}>
                      {isSelected && <Check size={16} aria-hidden />}
                      <span className="sr-only">{t("select")}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {groupProblem && <p className="mt-3 text-sm text-red-700">{groupProblem}</p>}
          {chosen.length > 0 && !groupProblem && (
            <SlotPicker mode="book" listingIds={chosen.map((l) => l.id)} minutes={minutes} onDone={() => setSelected([])} />
          )}
        </section>
      )}

      {data && data.listings.length > 0 && (
        <p className="mt-8 flex items-start gap-2 text-sm text-gray-500"><Phone size={16} aria-hidden className="mt-0.5 shrink-0" /> {t("noInternet")}</p>
      )}
    </div>
  );
}

function AppointmentCard({ appointment, onMove }: { appointment: HostAppointment; onMove: () => void }) {
  const t = useTranslations("hostVisit");
  const { formatDate } = useFormat();
  const date = formatDate(appointment.start, { timeZone: TIMEZONE, weekday: "long", day: "numeric", month: "long" });
  return (
    <li className="rounded-2xl bg-primary text-white p-5">
      <p className="flex items-center gap-2 font-heading font-bold text-lg">
        <CalendarCheck size={20} aria-hidden /> {t("booked", { date, time: hourMinute(appointment.start) })}
      </p>
      <ul className="mt-2 text-sm text-white/90">
        {appointment.listings.map((l) => <li key={l.id}>{l.title}</li>)}
      </ul>
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-white/90 mt-2">
        <span className="inline-flex items-center gap-1"><MapPin size={14} aria-hidden /> {appointment.city}</span>
        <span className="inline-flex items-center gap-1"><Clock size={14} aria-hidden /> {hourMinute(appointment.start)} – {hourMinute(appointment.end)}</span>
        {appointment.origin === "phone" && <span className="inline-flex items-center gap-1"><Phone size={14} aria-hidden /> {t("byPhone")}</span>}
      </p>
      {appointment.on_the_way_at && (
        <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-accent text-dark text-sm font-bold px-3 py-1">
          <Navigation size={14} aria-hidden /> {t("onTheWay")}
        </p>
      )}
      <div className="mt-4">
        {appointment.movable ? (
          <button type="button" onClick={onMove} className="rounded-xl bg-white text-primary font-bold px-4 py-2.5 text-sm">{t("move")}</button>
        ) : (
          <p className="text-xs text-white/80">{t("notMovable")}</p>
        )}
      </div>
    </li>
  );
}

type PickerProps = { minutes: number; onDone: () => void } & (
  | { mode: "book"; listingIds: string[] }
  | { mode: "move"; appointment: HostAppointment }
);

function SlotPicker(props: PickerProps) {
  const t = useTranslations("hostVisit");
  const { formatDate } = useFormat();
  const freeSlots = useFreeSlots(props.mode === "book" ? props.listingIds : []);
  const moveSlots = useMoveSlots(props.mode === "move" ? props.appointment.id : null);
  const { data: slots = [], isLoading } = props.mode === "book" ? freeSlots : moveSlots;
  const days = useMemo(() => slotsByDay(slots), [slots]);
  const [day, setDay] = useState<string | null>(null);
  const [slot, setSlot] = useState<string | null>(null);
  const action = useAgendaMutation((start: string) => (props.mode === "book"
    ? bookVisit(props.listingIds, start) : moveVisit(props.appointment.id, start)));

  const currentDay = day && days.some(([key]) => key === day) ? day : days[0]?.[0];
  const ofDay = days.find(([key]) => key === currentDay)?.[1] ?? [];
  const label = (iso: string) => ({
    date: formatDate(iso, { timeZone: TIMEZONE, weekday: "long", day: "numeric", month: "long" }),
    time: hourMinute(iso),
  });

  return (
    <section className="mt-5 rounded-2xl bg-white border border-gray-100 shadow-xs p-4 sm:p-5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-heading font-bold text-dark">{props.mode === "book" ? t("chooseSlot") : t("moveTitle")}</h3>
        <span className="text-sm text-gray-500">{formatDuration(props.minutes)}</span>
      </div>
      {isLoading && <p className="mt-3 text-sm text-gray-500">{t("loading")}</p>}
      {!isLoading && days.length === 0 && <p className="mt-3 text-sm text-gray-500">{t("noSlot")}</p>}
      {days.length > 0 && (
        <>
          <div className="flex gap-2 overflow-x-auto scrollbar-hide mt-3 pb-1" role="tablist">
            {days.map(([key, items]) => {
              const isCurrent = key === currentDay;
              const date = new Date(items[0]);
              return (
                <button key={key} type="button" role="tab" aria-selected={isCurrent} onClick={() => { setDay(key); setSlot(null); }}
                  className={cn("shrink-0 rounded-xl px-3 py-2 text-center min-w-18", isCurrent ? "bg-primary text-white" : "bg-light text-dark")}>
                  <span className="block text-xs font-semibold capitalize">{formatDate(items[0], { timeZone: TIMEZONE, weekday: "short" })}</span>
                  <span className="block font-heading font-bold text-lg">{formatDate(date.toISOString(), { timeZone: TIMEZONE, day: "numeric" })}</span>
                  <span className="block text-[11px] capitalize">{formatDate(items[0], { timeZone: TIMEZONE, month: "short" })}</span>
                </button>
              );
            })}
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mt-3">
            {ofDay.map((iso) => (
              <button key={iso} type="button" onClick={() => setSlot(iso)} aria-pressed={slot === iso}
                className={cn("rounded-xl border py-2.5 text-sm font-bold", slot === iso ? "bg-primary border-primary text-white" : "border-gray-200 text-dark")}>
                {hourMinute(iso)}
              </button>
            ))}
          </div>
        </>
      )}
      <div className="flex flex-wrap gap-2 mt-4">
        {slot && (
          <button type="button" disabled={action.isPending} onClick={() => action.mutate(slot, {
            onSuccess: () => { toast.success(props.mode === "book" ? t("confirmed") : t("movedToast")); props.onDone(); },
            onError: (err) => toast.error(apiErrorMessage(err)),
          })} className="rounded-xl bg-secondary text-white font-bold px-5 py-3 text-sm disabled:opacity-60">
            {props.mode === "book" ? t("confirm", label(slot)) : t("confirmMove", label(slot))}
          </button>
        )}
        <button type="button" onClick={props.onDone} className="rounded-xl px-4 py-3 text-sm font-semibold text-dark">{t("cancel")}</button>
      </div>
    </section>
  );
}
