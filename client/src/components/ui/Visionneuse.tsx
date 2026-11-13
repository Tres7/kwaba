"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { bornerPhoto, photosAcharger, voisines } from "./visionneuse-photos";

interface VisionneuseProps {
  photos: string[];
  /** Photo shown at the opening. */
  depart: number;
  /** Name of the gallery (the listing), for screen readers and the text alternatives. */
  nom: string;
  /** Caption of a photo, its room for example. */
  legende?: (url: string) => string | undefined;
  /** Under the caption, an action on the photo shown (an agent removes it without leaving the viewer). */
  action?: (url: string) => ReactNode;
  /** Closing, with the last photo shown: the page can bring its own carousel to it. */
  onClose: (derniere: number) => void;
}

const sansAnimation = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const ENTREE_HISTORIQUE = "kwabaVisionneuse";

/**
 * Full-screen photo viewer: arrows, swipe, keyboard (arrows, Home, End, Escape) and a "3 / 12" counter.
 * The swipe is the browser's own scrolling with snap points: on an iPhone the photo follows the finger and
 * a flick moves one photo only. Stops at the first and the last photo. Only the photo shown and its neighbours are loaded.
 * The back button closes it. Mount it to open, unmount it in `onClose`: each opening starts from `depart`.
 */
export default function Visionneuse({ photos, depart, nom, legende, action, onClose }: VisionneuseProps) {
  const t = useTranslations("visionneuse");
  const total = photos.length;
  const [index, setIndex] = useState(() => bornerPhoto(depart, total));
  const [chargees, setChargees] = useState(() => new Set(voisines(bornerPhoto(depart, total), total)));
  const rail = useRef<HTMLDivElement>(null);
  const dialogue = useRef<HTMLDivElement>(null);
  const boutonFermer = useRef<HTMLButtonElement>(null);
  // Read by the keyboard and resize handlers, which are not recreated at each photo
  const indexCourant = useRef(index);
  useEffect(() => { indexCourant.current = index; }, [index]);

  const fermer = useRef(onClose);
  useEffect(() => { fermer.current = onClose; }, [onClose]);
  const enFermeture = useRef(false);

  // Close button, Escape, click beside the photo: through the viewer's history entry when it is there
  const quitter = useCallback(() => {
    if (enFermeture.current) return;
    // Escape pressed twice must not go back twice (and leave the page)
    enFermeture.current = true;
    if (window.history.state?.[ENTREE_HISTORIQUE]) window.history.back();
    else fermer.current(indexCourant.current);
  }, []);

  // A history entry while open: the back button (Android) or the swipe-back gesture closes the photo instead of
  // leaving the listing. Same address, and Next.js's own state is kept in the entry (no reload when going back).
  useEffect(() => {
    // Already there in development (effects run twice) or after a reload with the viewer open
    if (!window.history.state?.[ENTREE_HISTORIQUE]) window.history.pushState({ ...window.history.state, [ENTREE_HISTORIQUE]: true }, "");
    const retour = () => fermer.current(indexCourant.current);
    window.addEventListener("popstate", retour);
    return () => window.removeEventListener("popstate", retour);
  }, []);

  const aller = useCallback((cible: number, instantane = false) => {
    const r = rail.current;
    if (!r) return;
    r.scrollTo({ left: bornerPhoto(cible, total) * r.clientWidth, behavior: instantane || sansAnimation() ? "auto" : "smooth" });
  }, [total]);

  // On the starting photo before the first paint
  useLayoutEffect(() => {
    const r = rail.current;
    if (r) r.scrollLeft = indexCourant.current * r.clientWidth;
  }, []);

  // Page frozen behind, focus inside the viewer, then back where it was
  useEffect(() => {
    const precedent = document.activeElement as HTMLElement | null;
    const debordement = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    boutonFermer.current?.focus();
    return () => {
      document.body.style.overflow = debordement;
      precedent?.focus({ preventScroll: true });
    };
  }, []);

  // A phone turned sideways: the rail changes width, the photo shown must stay the same
  useEffect(() => {
    const r = rail.current;
    if (!r) return;
    let largeur = r.clientWidth;
    const observateur = new ResizeObserver(() => {
      if (r.clientWidth === largeur) return;
      largeur = r.clientWidth;
      r.scrollLeft = indexCourant.current * largeur;
    });
    observateur.observe(r);
    return () => observateur.disconnect();
  }, []);

  useEffect(() => {
    const garderFocus = (e: KeyboardEvent) => {
      const boutons = Array.from(dialogue.current?.querySelectorAll<HTMLElement>("button") ?? []);
      if (!boutons.length) return;
      const premier = boutons[0];
      const dernier = boutons[boutons.length - 1];
      const dehors = !dialogue.current?.contains(document.activeElement);
      if (e.shiftKey && (dehors || document.activeElement === premier)) { e.preventDefault(); dernier.focus(); }
      else if (!e.shiftKey && (dehors || document.activeElement === dernier)) { e.preventDefault(); premier.focus(); }
    };
    const touche = (e: KeyboardEvent) => {
      // Alt + arrow is the browser's back / forward
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const actions: Record<string, () => void> = {
        Escape: quitter,
        ArrowLeft: () => aller(indexCourant.current - 1),
        ArrowRight: () => aller(indexCourant.current + 1),
        Home: () => aller(0, true),
        End: () => aller(total - 1, true),
      };
      if (e.key === "Tab") return garderFocus(e);
      const action = actions[e.key];
      if (!action) return;
      e.preventDefault();
      action();
    };
    document.addEventListener("keydown", touche);
    return () => document.removeEventListener("keydown", touche);
  }, [aller, quitter, total]);

  const suivreDefilement = () => {
    const r = rail.current;
    if (!r?.clientWidth) return;
    const i = bornerPhoto(Math.round(r.scrollLeft / r.clientWidth), total);
    setIndex(i);
    setChargees((c) => photosAcharger(c, i, total));
  };

  const fleche = "absolute top-1/2 -translate-y-1/2 w-11 h-11 sm:w-12 sm:h-12 rounded-full bg-black/50 sm:bg-white/10 text-white flex items-center justify-center hover:bg-white/20 transition-opacity focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-surface aria-disabled:opacity-30 aria-disabled:cursor-default";
  const legendeCourante = legende?.(photos[index]);

  return createPortal(
    // Above the cookie banner (z-[105]), under the cookie settings (z-[110])
    <motion.div ref={dialogue} role="dialog" aria-modal="true" aria-label={t("titre", { nom })}
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}
      className="fixed inset-0 z-106 flex flex-col bg-black text-white">
      <div className="flex items-center justify-between gap-3 px-3 sm:px-5 pt-[max(0.5rem,env(safe-area-inset-top))] pb-2 shrink-0">
        <p className="pl-2 text-sm font-semibold tabular-nums" aria-live="polite">
          <span aria-hidden>{index + 1} / {total}</span>
          <span className="sr-only">{t("position", { numero: index + 1, total })}</span>
        </p>
        <button ref={boutonFermer} type="button" onClick={quitter} aria-label={t("fermer")}
          className="w-11 h-11 rounded-full flex items-center justify-center hover:bg-white/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-surface">
          <X size={24} aria-hidden />
        </button>
      </div>

      <div className="relative flex-1 min-h-0">
        {/* pan-x: a vertical swipe does not move the page behind; pinch-zoom: the photo can still be enlarged */}
        <div ref={rail} onScroll={suivreDefilement}
          className="h-full flex overflow-x-auto overflow-y-hidden snap-x snap-mandatory overscroll-x-contain scrollbar-hide [touch-action:pan-x_pinch-zoom]">
          {photos.map((url, i) => (
            // A click beside the photo closes, like on most viewers (Escape on a keyboard)
            <div key={`${i}-${url}`} onClick={(e) => e.target === e.currentTarget && quitter()} aria-hidden={i !== index || undefined}
              className="w-full h-full shrink-0 snap-center snap-always flex items-center justify-center sm:px-20">
              {chargees.has(i) && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={url} alt={t("photo", { nom, numero: i + 1, total })} decoding="async" draggable={false}
                  className="max-w-full max-h-full object-contain select-none" />
              )}
            </div>
          ))}
        </div>
        {total > 1 && (
          <>
            <button type="button" onClick={() => aller(index - 1)} aria-label={t("precedente")} aria-disabled={index === 0}
              className={cn(fleche, "left-2 sm:left-5")}>
              <ChevronLeft size={26} aria-hidden />
            </button>
            <button type="button" onClick={() => aller(index + 1)} aria-label={t("suivante")} aria-disabled={index === total - 1}
              className={cn(fleche, "right-2 sm:right-5")}>
              <ChevronRight size={26} aria-hidden />
            </button>
          </>
        )}
      </div>

      <div className="min-h-12 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] flex flex-col items-center gap-2 shrink-0">
        <p className="text-center text-sm font-semibold">{legendeCourante}</p>
        {action?.(photos[index])}
      </div>
    </motion.div>,
    document.body,
  );
}
