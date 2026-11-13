"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import {
  ArrowLeft, CalendarPlus, CheckCircle2, Clock, Mail, MapPin, Navigation, Phone, Send, ShieldQuestion, UserRound, XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";
import { appointmentIcsUrl, cancelAppointment, concludePostCheck, onTheWay, reassignAppointment } from "../api";
import { useAgendaMutation, useAgents, useAppointment } from "../hooks";
import { durationMinutes, formatDuration, hourMinute, itineraryUrl } from "../time";

const FULL_DATE = new Intl.DateTimeFormat("fr-FR", { timeZone: "Africa/Lome", weekday: "long", day: "numeric", month: "long", year: "numeric" });

export default function AppointmentDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: session } = useSession();
  const isAdmin = session?.user?.role === "admin";
  const { data: appointment, isLoading, isError } = useAppointment(id);
  const { data: agents } = useAgents(isAdmin);
  const [reason, setReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [newAgent, setNewAgent] = useState("");
  const [finding, setFinding] = useState("");
  const [reporting, setReporting] = useState(false);

  const onTheWayMutation = useAgendaMutation(() => onTheWay(id));
  const cancelMutation = useAgendaMutation(() => cancelAppointment(id, reason));
  const reassignMutation = useAgendaMutation(() => reassignAppointment(id, newAgent));
  const postCheckMutation = useAgendaMutation((compliant: boolean) => concludePostCheck(id, compliant, finding));

  if (isLoading) return <p className="text-sm text-gray-500">Chargement…</p>;
  if (isError || !appointment) {
    return (
      <div>
        <BackLink />
        <p className="mt-6 text-sm text-red-700">Ce rendez-vous est introuvable.</p>
      </div>
    );
  }

  const confirmed = appointment.status === "confirmed";
  const mine = appointment.agent?.id === session?.user?.id;

  return (
    <div className="max-w-2xl">
      <BackLink />
      <div className="mt-4 rounded-3xl bg-surface shadow-xs p-6">
        <Status status={appointment.status} />
        <h1 className="font-heading font-bold text-2xl text-dark mt-2">{appointment.title}</h1>
        <p className="flex items-start gap-2 text-dark mt-3">
          <Clock size={18} aria-hidden className="text-gray-500 mt-0.5 shrink-0" />
          <span>
            <span className="block first-letter:uppercase">{FULL_DATE.format(new Date(appointment.start))}</span>
            {hourMinute(appointment.start)} – {hourMinute(appointment.end)}{" "}
            <span className="text-gray-500">({formatDuration(durationMinutes(appointment.start, appointment.end))})</span>
          </span>
        </p>
        <p className="flex items-start gap-2 text-dark mt-2">
          <MapPin size={18} aria-hidden className="text-gray-500 mt-0.5" />
          <span>{appointment.address ? `${appointment.address}, ` : ""}{appointment.city}</span>
        </p>
        {appointment.origin === "phone" && (
          <p className="flex items-center gap-2 text-sm text-gray-500 mt-2"><Phone size={16} aria-hidden /> Confirmé par téléphone</p>
        )}
        {appointment.listings.length > 1 && (
          <div className="mt-4">
            <p className="text-sm font-bold text-dark">Visite groupée · {appointment.listings.length} annonces</p>
            <ul className="mt-1 text-sm text-dark list-disc pl-5">{appointment.listings.map((l) => <li key={l.id}>{l.title}</li>)}</ul>
          </div>
        )}
        {appointment.closing_reason && (
          <p className="mt-4 text-sm text-gray-600">Clôture : {appointment.closing_reason}</p>
        )}
        {appointment.cancellation_reason && (
          <p className="mt-4 text-sm text-red-700">Motif d&apos;annulation : {appointment.cancellation_reason}</p>
        )}
        {isAdmin && appointment.agent && <p className="mt-4 text-sm text-gray-500">Agent : {appointment.agent.name}</p>}

        {appointment.host && (
          <div className="mt-5 rounded-2xl bg-light p-4">
            <p className="flex items-center gap-2 font-bold text-dark"><UserRound size={18} aria-hidden /> {appointment.host.name}</p>
            <div className="flex flex-wrap gap-2 mt-3">
              {appointment.host.phone && (
                <a href={`tel:${appointment.host.phone}`} className="inline-flex items-center gap-1.5 rounded-xl bg-surface px-3 py-2 text-sm font-semibold text-dark">
                  <Phone size={16} aria-hidden /> {appointment.host.phone}
                </a>
              )}
              <a href={`mailto:${appointment.host.email}`} className="inline-flex items-center gap-1.5 rounded-xl bg-surface px-3 py-2 text-sm font-semibold text-dark">
                <Mail size={16} aria-hidden /> Email
              </a>
            </div>
          </div>
        )}

        <div className="grid sm:grid-cols-2 gap-3 mt-6">
          <a href={itineraryUrl(appointment.position, appointment.address, appointment.city)} target="_blank" rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 rounded-2xl bg-primary text-white font-bold py-3.5">
            <Navigation size={18} aria-hidden /> Lancer l&apos;itinéraire
          </a>
          <a href={appointmentIcsUrl(appointment.id)}
            className="flex items-center justify-center gap-2 rounded-2xl bg-surface border border-gray-200 text-dark font-bold py-3.5">
            <CalendarPlus size={18} aria-hidden /> Ajouter à mon calendrier
          </a>
          {confirmed && mine && (
            <button type="button" disabled={onTheWayMutation.isPending || !!appointment.on_the_way_at}
              onClick={() => onTheWayMutation.mutate(undefined, {
                onSuccess: () => toast.success("L'hôte est prévenu que vous êtes en route."),
                onError: (e) => toast.error(apiErrorMessage(e, "Impossible de prévenir l'hôte.")),
              })}
              className="sm:col-span-2 flex items-center justify-center gap-2 rounded-2xl bg-secondary text-white font-bold py-3.5 disabled:opacity-60">
              <Send size={18} aria-hidden /> {appointment.on_the_way_at ? "Hôte prévenu : vous êtes en route" : "Je suis en route"}
            </button>
          )}
        </div>
      </div>

      {confirmed && appointment.post_check && (mine || isAdmin) && (
        <div className="mt-4 rounded-3xl border border-amber-200 bg-amber-50 p-6">
          <p className="flex items-center gap-2 font-bold text-amber-900"><ShieldQuestion size={18} aria-hidden /> Contrôle a posteriori</p>
          <p className="text-sm text-amber-900 mt-1">
            L&apos;annonce a été validée sans visite par un administrateur. Vérifiez sur place qu&apos;elle correspond au logement, puis concluez.
          </p>
          {!reporting ? (
            <div className="grid sm:grid-cols-2 gap-2 mt-4">
              <button type="button" disabled={postCheckMutation.isPending}
                onClick={() => postCheckMutation.mutate(true, {
                  onSuccess: () => toast.success("Contrôle conforme enregistré."),
                  onError: (err) => toast.error(apiErrorMessage(err, "Enregistrement impossible.")),
                })}
                className="flex items-center justify-center gap-2 rounded-2xl bg-primary text-white font-bold py-3 disabled:opacity-60">
                <CheckCircle2 size={18} aria-hidden /> Conforme
              </button>
              <button type="button" onClick={() => setReporting(true)}
                className="flex items-center justify-center gap-2 rounded-2xl bg-surface border border-red-200 text-red-700 font-bold py-3">
                <XCircle size={18} aria-hidden /> Non conforme
              </button>
            </div>
          ) : (
            <form className="mt-4" onSubmit={(e) => {
              e.preventDefault();
              postCheckMutation.mutate(false, {
                onSuccess: () => toast.success("Annonce retirée du site : l'hôte et les admins sont prévenus."),
                onError: (err) => toast.error(apiErrorMessage(err, "Enregistrement impossible.")),
              });
            }}>
              <label htmlFor="finding" className="block text-sm font-bold text-dark">Ce qui n&apos;est pas conforme (envoyé à l&apos;hôte)</label>
              <textarea id="finding" value={finding} onChange={(e) => setFinding(e.target.value)} rows={3} required minLength={10}
                className="mt-2 w-full rounded-xl border border-gray-200 p-3 text-sm bg-surface" />
              <div className="flex gap-2 mt-3">
                <button type="submit" disabled={postCheckMutation.isPending}
                  className="rounded-xl bg-red-700 dark:bg-red-600 text-white font-bold px-4 py-2.5 text-sm disabled:opacity-60">Retirer l&apos;annonce du site</button>
                <button type="button" onClick={() => setReporting(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-dark">Retour</button>
              </div>
            </form>
          )}
        </div>
      )}

      {confirmed && (mine || isAdmin) && (
        <div className="mt-4 rounded-3xl bg-surface shadow-xs p-6">
          {!cancelling ? (
            <button type="button" onClick={() => setCancelling(true)} className="text-sm font-bold text-red-700">
              Annuler cette visite
            </button>
          ) : (
            <form onSubmit={(e) => {
              e.preventDefault();
              cancelMutation.mutate(undefined, {
                onSuccess: () => { toast.success("Visite annulée : l'hôte est prévenu."); setCancelling(false); },
                onError: (err) => toast.error(apiErrorMessage(err, "Annulation impossible.")),
              });
            }}>
              <label htmlFor="reason" className="block text-sm font-bold text-dark">Motif, envoyé à l&apos;hôte</label>
              <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} required minLength={5}
                className="mt-2 w-full rounded-xl border border-gray-200 p-3 text-sm" />
              <p className="text-xs text-gray-500 mt-1">L&apos;annonce retourne dans la file « À faire » et l&apos;hôte pourra réserver un autre créneau.</p>
              <div className="flex gap-2 mt-3">
                <button type="submit" disabled={cancelMutation.isPending}
                  className="rounded-xl bg-red-700 dark:bg-red-600 text-white font-bold px-4 py-2.5 text-sm disabled:opacity-60">Confirmer l&apos;annulation</button>
                <button type="button" onClick={() => setCancelling(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-dark">Garder la visite</button>
              </div>
            </form>
          )}
        </div>
      )}

      {confirmed && isAdmin && (
        <form className="mt-4 rounded-3xl bg-surface shadow-xs p-6" onSubmit={(e) => {
          e.preventDefault();
          reassignMutation.mutate(undefined, {
            onSuccess: () => toast.success("Visite réaffectée."),
            onError: (err) => toast.error(apiErrorMessage(err, "Réaffectation impossible.")),
          });
        }}>
          <label htmlFor="agent" className="block text-sm font-bold text-dark">Réaffecter à un autre agent</label>
          <div className="flex flex-wrap gap-2 mt-2">
            <select id="agent" value={newAgent} onChange={(e) => setNewAgent(e.target.value)} required
              className="flex-1 min-w-0 rounded-xl border border-gray-200 px-3 py-2.5 text-sm">
              <option value="">Choisir un agent</option>
              {agents?.filter((a) => a.id !== appointment.agent?.id).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <button type="submit" disabled={!newAgent || reassignMutation.isPending}
              className="rounded-xl bg-primary text-white font-bold px-4 py-2.5 text-sm disabled:opacity-60">Réaffecter</button>
          </div>
        </form>
      )}
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/agent/agenda" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand">
      <ArrowLeft size={16} aria-hidden /> Agenda
    </Link>
  );
}

function Status({ status }: { status: string }) {
  const map: Record<string, { label: string; icon: typeof CheckCircle2; className: string }> = {
    confirmed: { label: "Confirmée", icon: CheckCircle2, className: "bg-primary/10 text-brand" },
    done: { label: "Terminée", icon: CheckCircle2, className: "bg-gray-100 text-dark" },
    cancelled: { label: "Annulée", icon: XCircle, className: "bg-red-50 text-red-700" },
  };
  const { label, icon: Icon, className } = map[status] ?? map.confirmed;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold", className)}>
      <Icon size={14} aria-hidden /> {label}
    </span>
  );
}
