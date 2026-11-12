"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  confirmReport, getReport, getSanction, liftSanction, rejectReport, reviewContest, setReportLegalHold,
  type AdminReport, type AdminSanction,
} from "@/features/messaging";
import { apiErrorMessage } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import Panneau, { Champ, Interrupteur, Zone } from "@/components/backoffice/Panneau";
import { ActionButton, Pill } from "@/components/backoffice/AdminTable";

const REASONS: Record<string, string> = {
  insult: "Insulte", hate: "Propos haineux", threat: "Menace", harassment: "Harcèlement", spam: "Spam", scam: "Arnaque", other: "Autre",
};
const STEPS: Record<string, string> = {
  reminder: "Rappel des règles", formal_warning: "Avertissement formel", short_suspension: "Suspension courte",
  long_suspension: "Suspension longue", admin_decision: "Décision à prendre (suspension du compte)",
};
const STATUSES: Record<string, string> = { pending: "À examiner", confirmed: "Confirmé", rejected: "Rejeté" };
const CONTESTS: Record<string, string> = { pending: "En attente", accepted: "Acceptée", rejected: "Rejetée" };

const dateTime = (iso: string | null) => (iso ? formatDate(iso, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");

function useDetail<T>(load: (id: number) => Promise<T>, id: number, onClose: () => void) {
  const [detail, setDetail] = useState<T | null>(null);
  useEffect(() => {
    load(id).then(setDetail).catch((err) => {
      toast.error(apiErrorMessage(err));
      onClose();
    });
  }, [load, id, onClose]);
  return [detail, setDetail] as const;
}

export function ReportPanel({ reportId, onClose, onDone }: { reportId: number; onClose: () => void; onDone: () => void }) {
  const [report, setReport] = useDetail<AdminReport>(getReport, reportId, onClose);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setSending(true);
    try {
      await action();
      toast.success(success);
      onDone();
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setSending(false);
    }
  };

  const toggleHold = async (hold: boolean) => {
    try {
      await setReportLegalHold(reportId, hold);
      setReport((current) => current && { ...current, legal_hold: hold });
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  return (
    <Panneau ouvert titre="Signalement" onFermer={onClose} envoi={sending}>
      {!report ? (
        <p className="text-sm text-muted">Chargement…</p>
      ) : (
        <div className="space-y-5 text-sm">
          <div className="space-y-1">
            <p><span className="text-muted">Auteur du message :</span> <strong>{report.author.nom}</strong> ({report.author.email})</p>
            <p><span className="text-muted">Signalé par :</span> {report.reporter.nom} ({report.reporter.email})</p>
            <p className="flex flex-wrap gap-2 items-center">
              <Pill ton={report.reason === "threat" ? "rouge" : "orange"}>{REASONS[report.reason]}</Pill>
              <Pill ton={report.status === "pending" ? "orange" : report.status === "confirmed" ? "rouge" : "gris"}>{STATUSES[report.status]}</Pill>
              <span className="text-muted">le {dateTime(report.created_at)}</span>
            </p>
            {report.details && <p className="bg-light rounded-xl px-3 py-2">{report.details}</p>}
          </div>

          <div>
            <p className="text-xs font-bold text-dark uppercase tracking-wide mb-2">Contexte figé au signalement</p>
            {report.context.length === 0 ? (
              <p className="text-muted">Contexte supprimé (durée de conservation écoulée).</p>
            ) : (
              <ol className="space-y-2">
                {report.context.map((m) => (
                  <li key={m.message_id} className={cn("rounded-xl px-3 py-2 border", m.reported ? "border-red-200 bg-red-50" : "border-gray-100",
                    m.from_author ? "mr-8" : "ml-8 bg-gray-50")}>
                    <p className="text-[11px] text-muted">{m.from_author ? "Auteur" : "Signaleur"} · {dateTime(m.created_at)}{m.reported && " · message signalé"}</p>
                    <p className="whitespace-pre-wrap break-words text-dark">{m.content}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <Interrupteur label="Conservation prolongée (plainte possible)" checked={report.legal_hold} onChange={toggleHold} />

          {report.status === "pending" ? (
            <>
              <Champ label="Note (facultative)">
                <Zone value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
              </Champ>
              <div className="flex flex-wrap gap-2">
                <ActionButton danger disabled={sending} onClick={() => run(() => confirmReport(reportId, note), "Signalement confirmé : sanction appliquée")}>
                  Confirmer et sanctionner
                </ActionButton>
                <ActionButton disabled={sending} onClick={() => run(() => rejectReport(reportId, note), "Signalement rejeté")}>
                  Rejeter
                </ActionButton>
              </div>
              <p className="text-xs text-muted">La sanction suit l&apos;échelle (rappel, avertissement, suspension) ; l&apos;auteur du signalement n&apos;est jamais nommé.</p>
            </>
          ) : (
            report.review_note && <p className="text-muted">Note : {report.review_note}</p>
          )}
        </div>
      )}
    </Panneau>
  );
}

export function SanctionPanel({ sanctionId, onClose, onDone }: { sanctionId: number; onClose: () => void; onDone: () => void }) {
  const [sanction] = useDetail<AdminSanction>(getSanction, sanctionId, onClose);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setSending(true);
    try {
      await action();
      toast.success(success);
      onDone();
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setSending(false);
    }
  };

  const active = !!sanction?.ends_at && !sanction.cancelled_at && new Date(sanction.ends_at).getTime() > Date.now()
    && (sanction.step === "short_suspension" || sanction.step === "long_suspension");

  return (
    <Panneau ouvert titre="Sanction" onFermer={onClose} envoi={sending}>
      {!sanction ? (
        <p className="text-sm text-muted">Chargement…</p>
      ) : (
        <div className="space-y-5 text-sm">
          <div className="space-y-1">
            {sanction.user && <p><span className="text-muted">Compte :</span> <strong>{sanction.user.nom}</strong> ({sanction.user.email})</p>}
            <p className="flex flex-wrap gap-2 items-center">
              <Pill ton="rouge">{STEPS[sanction.step]}</Pill>
              <Pill ton="gris">{REASONS[sanction.category]}</Pill>
              {sanction.cancelled_at && <Pill ton="vert">Annulée</Pill>}
            </p>
            <p className="text-muted">Appliquée le {dateTime(sanction.created_at)}{sanction.ends_at && ` · fin le ${dateTime(sanction.ends_at)}`}</p>
          </div>

          {sanction.contest_status && (
            <div className="space-y-2">
              <p className="text-xs font-bold text-dark uppercase tracking-wide">Contestation · {CONTESTS[sanction.contest_status]}</p>
              <p className="bg-light rounded-xl px-3 py-2 whitespace-pre-wrap">{sanction.contest_text || "Texte supprimé (durée de conservation écoulée)."}</p>
              {sanction.contest_note && <p className="text-muted">Note : {sanction.contest_note}</p>}
            </div>
          )}

          {sanction.contest_status === "pending" && (
            <>
              <Champ label="Note (facultative)" aide="À examiner par un autre administrateur que celui qui a confirmé le signalement, si possible.">
                <Zone value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
              </Champ>
              <div className="flex flex-wrap gap-2">
                <ActionButton disabled={sending} onClick={() => run(() => reviewContest(sanctionId, true, note), "Contestation acceptée : sanction annulée")}>
                  Accepter (annuler la sanction)
                </ActionButton>
                <ActionButton danger disabled={sending} onClick={() => run(() => reviewContest(sanctionId, false, note), "Contestation rejetée")}>
                  Rejeter
                </ActionButton>
              </div>
            </>
          )}

          {active && (
            <ActionButton disabled={sending} onClick={() => run(() => liftSanction(sanctionId), "Suspension levée")}>
              Lever la suspension maintenant
            </ActionButton>
          )}
        </div>
      )}
    </Panneau>
  );
}
