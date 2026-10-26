"use client";

import { useId, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import Floating from "@/components/ui/Floating";
import { usePopover } from "@/lib/usePopover";
import { cn } from "@/lib/utils";

export interface SelectOption<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

interface SelectProps<T extends string> {
  value: T;
  onChange: (v: T) => void;
  options: SelectOption<T>[];
  /** Accessible name of the field (read by screen readers). */
  label: string;
  id?: string;
  icon?: React.ReactNode;
  className?: string;
  buttonClassName?: string;
}

/** Custom dropdown: mouse, touch and keyboard (arrows, Enter, Escape). */
export default function Select<T extends string>({ value, onChange, options, label, id, icon, className, buttonClassName }: SelectProps<T>) {
  const t = useTranslations("commun");
  const { open, setOpen, ref, panelRef } = usePopover();
  const listId = useId();
  const [actif, setActif] = useState(0);
  const courant = options.find((o) => o.value === value);

  const ouvrir = () => {
    setActif(Math.max(0, options.findIndex((o) => o.value === value)));
    setOpen(true);
  };

  const choisir = (o: SelectOption<T>) => {
    onChange(o.value);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      ouvrir();
      return;
    }
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActif((i) => Math.min(options.length - 1, i + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActif((i) => Math.max(0, i - 1)); }
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisir(options[actif]); }
    if (e.key === "Tab") setOpen(false);
  };

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        id={id} type="button" role="combobox" aria-label={label} aria-expanded={open} aria-controls={listId}
        aria-activedescendant={open ? `${listId}-${actif}` : undefined}
        onClick={() => (open ? setOpen(false) : ouvrir())} onKeyDown={onKeyDown}
        className={cn(
          "w-full flex items-center gap-2 text-left border border-gray-200 rounded-xl px-4 py-3 bg-white hover:border-gray-300 transition-colors",
          open && "border-primary ring-2 ring-primary/20",
          buttonClassName,
        )}
      >
        {icon}
        <span className="flex-1 min-w-0 truncate text-base sm:text-sm font-medium text-dark">{courant?.label ?? t("choisir")}</span>
        <ChevronDown size={16} className={cn("text-gray-400 transition-transform flex-shrink-0", open && "rotate-180")} />
      </button>

      {open && (
        <Floating ref={panelRef} anchor={ref} onClose={() => setOpen(false)} label={label} className="max-h-72 p-1.5">
        <ul id={listId} role="listbox" aria-label={label}>
          {options.map((o, i) => {
            const selectionne = o.value === value;
            return (
              <li
                key={o.value} id={`${listId}-${i}`} role="option" aria-selected={selectionne}
                onClick={() => choisir(o)} onMouseEnter={() => setActif(i)}
                className={cn("flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer text-sm", i === actif && "bg-gray-50", selectionne && "font-semibold text-primary")}
              >
                <span className="flex-1 min-w-0">
                  <span className="block truncate">{o.label}</span>
                  {o.hint && <span className="block text-xs text-muted font-normal">{o.hint}</span>}
                </span>
                {selectionne && <Check size={16} className="flex-shrink-0" />}
              </li>
            );
          })}
        </ul>
        </Floating>
      )}
    </div>
  );
}
