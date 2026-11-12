"use client";

import { useEffect, useId, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Info, RotateCcw, TriangleAlert } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { saveAgendaSettings } from "../api";
import { agendaKeys, useAgendaSettings } from "../hooks";
import { SECTIONS, durationOptions, type SettingField } from "../settingsHelp";
import { formatDuration } from "../time";
import type { AgendaSettingsValues } from "../types";

const UPDATED = new Intl.DateTimeFormat("fr-FR", { timeZone: "Africa/Lome", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
const inputClass = "w-20 sm:w-24 px-3 py-2 border border-gray-200 rounded-xl text-right tabular-nums text-base sm:text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";

function display(field: SettingField, value: number): string {
  return field.kind === "duration" ? formatDuration(value) : `${value} ${field.unit?.(value) ?? ""}`.trim();
}

export default function AgendaSettings() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useAgendaSettings();
  const [values, setValues] = useState<AgendaSettingsValues | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data) setValues(data.values);
  }, [data]);

  if (isLoading || (!values && !isError)) return <div className="h-96 skeleton rounded-2xl" />;
  if (isError || !data || !values) return <p className="text-sm text-red-700">Les réglages n&apos;ont pas pu être chargés.</p>;

  const changed = (Object.keys(values) as (keyof AgendaSettingsValues)[]).filter((k) => values[k] !== data.values[k]);

  const save = async () => {
    setSaving(true);
    setErrors({});
    try {
      await saveAgendaSettings(values);
      toast.success("Réglages enregistrés : ils s'appliquent aux prochaines réservations.");
      queryClient.invalidateQueries({ queryKey: agendaKeys.all });
    } catch (err) {
      const fieldErrors = (err as { response?: { data?: { errors?: Record<string, string> } } })?.response?.data?.errors;
      if (fieldErrors) setErrors(fieldErrors);
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <p className="flex items-start gap-2 rounded-2xl bg-amber-50 text-amber-900 px-4 py-3 text-sm">
        <TriangleAlert size={18} className="flex-shrink-0 mt-0.5" aria-hidden />
        <span>
          Un changement s&apos;applique aux réservations faites ensuite. Une visite déjà confirmée garde sa durée et son écart.
          Chaque modification est enregistrée dans le journal d&apos;audit.
        </span>
      </p>

      {SECTIONS.map((section) => (
        <section key={section.title} className="bg-white rounded-2xl border border-gray-100 p-5">
          <h2 className="font-heading font-bold text-dark mb-2">{section.title}</h2>
          <div className="divide-y divide-gray-100">
            {section.fields.map((field) => (
              <SettingRow key={field.key} field={field} values={values} defaultValue={data.defaults[field.key]}
                bounds={data.bounds[field.key]} error={errors[field.key]}
                onChange={(value) => setValues({ ...values, [field.key]: value })} />
            ))}
          </div>
        </section>
      ))}

      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-xs text-muted">
          {data.updated_at ? `Modifiés le ${UPDATED.format(new Date(data.updated_at))}${data.updated_by ? ` par ${data.updated_by}` : ""}` : "Règles d'origine, jamais modifiées"}
        </p>
        <div className="flex gap-2">
          <button type="button" onClick={() => setValues(data.defaults)}
            className="inline-flex items-center gap-1.5 px-4 py-3 rounded-xl text-sm font-semibold text-dark hover:bg-gray-100">
            <RotateCcw size={15} aria-hidden /> Valeurs d&apos;origine
          </button>
          <button type="button" onClick={save} disabled={saving || changed.length === 0}
            className="px-6 py-3 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary-600 disabled:opacity-50">
            {saving ? "Enregistrement…" : changed.length ? `Enregistrer (${changed.length})` : "Aucun changement"}
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingRow({ field, values, defaultValue, bounds, error, onChange }: {
  field: SettingField; values: AgendaSettingsValues; defaultValue: number; bounds: { min: number; max: number };
  error?: string; onChange: (value: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const helpId = useId();
  const inputId = useId();
  const value = values[field.key];

  return (
    <div className="py-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 flex items-center gap-1.5">
          <label htmlFor={inputId} className="text-sm font-semibold text-dark">{field.label}</label>
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls={helpId}
            aria-label={`À quoi sert « ${field.label} » ?`}
            className={cn("w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
              open ? "bg-primary text-white" : "text-gray-500 hover:bg-gray-100")}>
            <Info size={15} aria-hidden />
          </button>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {field.kind === "duration" ? (
            <select id={inputId} value={value} onChange={(e) => onChange(Number(e.target.value))}
              className={cn(inputClass, "w-28 text-left")}>
              {durationOptions(bounds.min, bounds.max).map((option) => (
                <option key={option} value={option}>{formatDuration(option)}</option>
              ))}
            </select>
          ) : (
            <>
              <input id={inputId} type="number" inputMode="numeric" min={bounds.min} max={bounds.max} value={value}
                onChange={(e) => onChange(Math.round(Number(e.target.value)))} className={inputClass} />
              <span className="w-14 sm:w-16 text-sm text-muted">{field.unit?.(value)}</span>
            </>
          )}
        </div>
      </div>
      <p className="text-xs text-muted mt-1">
        {value !== defaultValue && <>D&apos;origine : {display(field, defaultValue)} · </>}
        Entre {display(field, bounds.min)} et {display(field, bounds.max)}
      </p>
      {error && <p role="alert" className="text-sm text-red-700 mt-1">{error}</p>}
      {open && (
        <p id={helpId} className="mt-2 rounded-xl bg-primary/5 text-dark text-sm px-4 py-3">{field.help(values)}</p>
      )}
    </div>
  );
}
