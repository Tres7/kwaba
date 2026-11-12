"use client";

import { useCallback, useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { contestSanction, getModerationStatus } from "./api";
import MessagingDialog from "./MessagingDialog";
import { isSuspended } from "./moderation";
import type { ModerationStatus, UserSanction } from "./types";

const CONTEST_MIN = 5;
const CONTEST_MAX = 1000;

export function useModerationStatus() {
  const [status, setStatus] = useState<ModerationStatus | null>(null);

  const reload = useCallback(() => {
    getModerationStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(reload, [reload]);

  const suspend = useCallback((until: string) => {
    setStatus((current) => ({ sanctions: current?.sanctions ?? [], suspended_until: until }));
  }, []);

  return { status, reload, suspend };
}

function ContestDialog({ sanction, onClose, onDone }: { sanction: UserSanction; onClose: () => void; onDone: () => void }) {
  const t = useTranslations("moderation");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    setSending(true);
    try {
      await contestSanction(sanction.id, text.trim());
      toast.success(t("contestSent"));
      onDone();
    } catch {
      toast.error(t("contestError"));
      setSending(false);
    }
  };

  return (
    <MessagingDialog
      title={t("contestTitle")} closeLabel={t("close")} submitLabel={t("send")} cancelLabel={t("cancel")}
      sending={sending} canSubmit={text.trim().length >= CONTEST_MIN} onClose={onClose} onSubmit={submit}
    >
      <p className="text-sm text-muted">{t("contestIntro")}</p>
      <label className="block">
        <span className="text-sm font-semibold text-dark">{t("contestLabel")}</span>
        <textarea
          value={text} onChange={(e) => setText(e.target.value)} maxLength={CONTEST_MAX} rows={4}
          className="mt-1 w-full rounded-xl border border-light px-3 py-2 text-sm text-dark outline-hidden focus:border-primary/40"
        />
      </label>
    </MessagingDialog>
  );
}

export default function ModerationNotice({ status, onChange }: { status: ModerationStatus | null; onChange: () => void }) {
  const t = useTranslations("moderation");
  const { formatDate } = useFormat();
  const [contesting, setContesting] = useState<UserSanction | null>(null);

  if (!status) return null;
  const suspended = isSuspended(status.suspended_until);
  const visible = status.sanctions.filter((s) => !s.cancelled && (s.contestable || s.contest_status === "pending"));
  if (!suspended && visible.length === 0) return null;

  const date = (iso: string) => formatDate(iso, { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="bg-red-50 border border-red-100 rounded-2xl px-4 py-3 text-sm text-dark space-y-2" role="status">
      <p className="flex items-center gap-2 font-semibold text-red-800">
        <ShieldAlert size={16} aria-hidden /> {t("sanctionsTitle")}
      </p>
      {suspended && status.suspended_until && <p>{t("suspended", { date: date(status.suspended_until) })}</p>}
      {visible.length > 0 && (
        <ul className="space-y-1.5">
          {visible.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>{t("sanctionLine", { step: t(`step.${s.step}`), date: date(s.created_at), reason: t(`reason.${s.category}`) })}</span>
              {s.contest_status ? (
                <span className="text-muted">{t(`contestStatus.${s.contest_status}`)}</span>
              ) : (
                <button type="button" onClick={() => setContesting(s)} className="font-semibold text-primary hover:underline">
                  {t("contest")}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {contesting && (
        <ContestDialog sanction={contesting} onClose={() => setContesting(null)} onDone={() => { setContesting(null); onChange(); }} />
      )}
    </div>
  );
}
