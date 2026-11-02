"use client";

import { useState } from "react";
import { Heart } from "lucide-react";
import { useSession } from "next-auth/react";
import { usePathname, useRouter } from "@/i18n/navigation";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { ajouterFavori, retirerFavori } from "./api";

interface FavoriteButtonProps {
  hebergementId: string;
  initial: boolean;
  onChange?: (isFavorite: boolean) => void;
  variant?: "icon" | "button";
  className?: string;
}

export default function FavoriteButton({ hebergementId, initial, onChange, variant = "icon", className }: FavoriteButtonProps) {
  const t = useTranslations("favoris");
  const { status } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [isFavorite, setIsFavorite] = useState(initial);
  const [pending, setPending] = useState(false);

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (status !== "authenticated") {
      router.push(`/login?callbackUrl=${encodeURIComponent(pathname)}`);
      return;
    }
    if (pending) return;

    const next = !isFavorite;
    setIsFavorite(next);
    setPending(true);
    try {
      await (next ? ajouterFavori : retirerFavori)(hebergementId);
      onChange?.(next);
      toast.success(next ? t("ajoute") : t("retire"));
    } catch {
      setIsFavorite(!next);
      toast.error(t("erreur"));
    } finally {
      setPending(false);
    }
  };

  if (variant === "button") {
    return (
      <button
        type="button"
        onClick={toggle}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? t("sauvegarde") : t("sauvegarder")}
        className={cn(
          "relative zone-tactile flex items-center gap-2 border border-gray-200 rounded-xl px-4 py-2 text-sm text-dark transition-colors hover:bg-light-muted",
          className
        )}
      >
        <Heart size={15} className={isFavorite ? "text-red-600 fill-red-500" : "text-dark"} />
        <span className="hidden sm:inline">{isFavorite ? t("sauvegarde") : t("sauvegarder")}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isFavorite ? t("retirer") : t("ajouter")}
      aria-pressed={isFavorite}
      className={cn(
        "zone-tactile p-2 bg-white/90 backdrop-blur-sm rounded-full shadow-sm transition-colors hover:bg-white",
        isFavorite ? "text-red-600" : "text-gray-500 hover:text-red-600",
        className
      )}
    >
      <Heart size={16} className={isFavorite ? "fill-red-500" : ""} />
    </button>
  );
}
