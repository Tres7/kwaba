"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type ThemeChoice = "light" | "dark" | "system";

export const THEME_CHOICES: { value: ThemeChoice; icon: LucideIcon }[] = [
  { value: "light", icon: Sun },
  { value: "dark", icon: Moon },
  { value: "system", icon: Monitor },
];

const subscribe = () => () => {};

export function useThemeChoice() {
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  return { choice: mounted ? (theme as ThemeChoice | undefined) : undefined, setChoice: (value: ThemeChoice) => setTheme(value) };
}

export default function ThemeSelector({ className, full = false }: { className?: string; full?: boolean }) {
  const t = useTranslations("theme");
  const { choice, setChoice } = useThemeChoice();

  return (
    <div role="group" aria-label={t("choose")} className={cn("inline-flex items-center gap-1 rounded-full border border-gray-200 p-0.5", className)}>
      {THEME_CHOICES.map(({ value, icon: Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => setChoice(value)}
          aria-pressed={choice === value}
          aria-label={full ? undefined : t(value)}
          title={t(value)}
          className={cn("inline-flex items-center gap-1.5 rounded-full py-1 text-xs font-bold transition-colors",
            full ? "px-2.5" : "px-2",
            choice === value ? "bg-primary text-white" : "text-dark hover:text-brand")}
        >
          <Icon size={14} aria-hidden />
          {full && t(value)}
        </button>
      ))}
    </div>
  );
}
