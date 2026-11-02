import { Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale, useTranslations } from "next-intl";

interface RatingBadgeProps {
  rating: number;
  count: number;
  /** compact : « ★ 4,8 » ; full : « ★ 4,8 (12 avis) » */
  variant?: "compact" | "full";
  className?: string;
}

/** Rating from verified reviews; "New" while no traveller has rated the listing. */
export default function RatingBadge({ rating, count, variant = "compact", className }: RatingBadgeProps) {
  const locale = useLocale();
  const t = useTranslations("note");
  if (count === 0) {
    return (
      <span className={cn("inline-flex items-center text-[11px] font-bold uppercase tracking-wide text-secondary bg-secondary/10 px-2 py-0.5 rounded-full", className)}>
        Nouveau
      </span>
    );
  }
  return (
    <span className={cn("inline-flex items-center gap-1", className)} aria-label={t("noteSur5", { note: rating.toFixed(1), nombre: count })}>
      <Star size={13} className="fill-accent text-accent" />
      <span className="text-xs font-bold text-dark">{rating.toLocaleString(locale === "en" ? "en-GB" : "fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</span>
      {variant === "full" && <span className="text-xs text-muted">({t("avis", { nombre: count })})</span>}
    </span>
  );
}
