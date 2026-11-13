"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

type Props = {
  title: string;
  closeLabel: string;
  submitLabel: string;
  cancelLabel: string;
  sending: boolean;
  canSubmit: boolean;
  onClose: () => void;
  onSubmit: () => void;
  children: React.ReactNode;
};

export default function MessagingDialog({ title, closeLabel, submitLabel, cancelLabel, sending, canSubmit, onClose, onSubmit, children }: Props) {
  const panel = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.querySelector<HTMLElement>("input, textarea, button")?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !sending) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [onClose, sending]);

  return createPortal(
    <div className="fixed inset-0 z-70 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-night/50" onClick={() => !sending && onClose()} aria-hidden="true" />
      <form
        ref={panel} role="dialog" aria-modal="true" aria-labelledby="messaging-dialog-title"
        onSubmit={(e) => { e.preventDefault(); if (canSubmit && !sending) onSubmit(); }}
        className="relative w-full sm:max-w-md bg-surface rounded-t-3xl sm:rounded-3xl shadow-xl p-6 max-h-[90vh] overflow-y-auto"
      >
        <button type="button" onClick={onClose} aria-label={closeLabel} className="absolute top-4 right-4 w-9 h-9 rounded-full flex items-center justify-center text-gray-600 hover:bg-gray-100">
          <X size={18} />
        </button>
        <h2 id="messaging-dialog-title" className="font-heading font-bold text-dark text-lg pr-10">{title}</h2>
        <div className="mt-4 space-y-4">{children}</div>
        <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <button type="button" onClick={onClose} disabled={sending} className="px-5 py-2.5 rounded-xl text-sm font-semibold text-dark hover:bg-light">
            {cancelLabel}
          </button>
          <button type="submit" disabled={!canSubmit || sending} className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-primary hover:bg-primary-600 disabled:opacity-50">
            {submitLabel}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
