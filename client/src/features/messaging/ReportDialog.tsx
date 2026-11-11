"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { reportMessage } from "./api";
import MessagingDialog from "./MessagingDialog";
import type { ReportReason } from "./types";

const REASONS: ReportReason[] = ["insult", "hate", "threat", "harassment", "spam", "scam", "other"];
const DETAILS_MAX = 500;

export default function ReportDialog({ conversationId, messageId, onClose }: { conversationId: string; messageId: number; onClose: () => void }) {
  const t = useTranslations("moderation");
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [details, setDetails] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    if (!reason) return;
    setSending(true);
    try {
      await reportMessage(conversationId, messageId, reason, details.trim());
      toast.success(t("reportSent"));
      onClose();
    } catch {
      toast.error(t("reportError"));
      setSending(false);
    }
  };

  return (
    <MessagingDialog
      title={t("reportTitle")} closeLabel={t("close")} submitLabel={t("send")} cancelLabel={t("cancel")}
      sending={sending} canSubmit={reason !== null} onClose={onClose} onSubmit={submit}
    >
      <p className="text-sm text-muted">{t("reportIntro")}</p>
      <fieldset>
        <legend className="text-sm font-semibold text-dark mb-2">{t("reasonLabel")}</legend>
        <div className="grid grid-cols-2 gap-2">
          {REASONS.map((r) => (
            <label key={r} className="flex items-center gap-2 text-sm text-dark rounded-xl border border-light px-3 py-2 cursor-pointer has-[:checked]:border-primary has-[:checked]:bg-primary/5">
              <input type="radio" name="report-reason" value={r} checked={reason === r} onChange={() => setReason(r)} className="accent-primary" />
              {t(`reason.${r}`)}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="block">
        <span className="text-sm font-semibold text-dark">{t("details")}</span>
        <textarea
          value={details} onChange={(e) => setDetails(e.target.value)} maxLength={DETAILS_MAX} rows={3}
          className="mt-1 w-full rounded-xl border border-light px-3 py-2 text-sm text-dark outline-none focus:border-primary/40"
        />
      </label>
    </MessagingDialog>
  );
}
