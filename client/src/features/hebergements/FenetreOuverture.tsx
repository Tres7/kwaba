"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslations } from "next-intl";
import { AnimatePresence, motion } from "framer-motion";
import { Home, Sparkle, X } from "lucide-react";

const FOCUSABLES = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

interface Props {
  ouverte: boolean;
  /** "Créer mon annonce": the host goes on to the listing form. */
  onCreer: () => void;
  /** "Plus tard", the close button, Escape or a click outside. */
  onFermer: () => void;
}

/** Pre-launch window shown to hosts when they open their space and before they create a listing. */
export default function FenetreOuverture({ ouverte, onCreer, onFermer }: Props) {
  const t = useTranslations("prelancement");
  const panneau = useRef<HTMLDivElement>(null);
  const bouton = useRef<HTMLButtonElement>(null);
  // Rendered on the client only (portal): no mismatch with the server HTML
  const [monte, setMonte] = useState(false);
  useEffect(() => setMonte(true), []);

  useEffect(() => {
    if (!ouverte) return;
    const precedent = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onFermer();
        return;
      }
      if (e.key !== "Tab" || !panneau.current) return;
      // Focus trap: Tab and Shift+Tab cycle through the window's controls only
      const elements = Array.from(panneau.current.querySelectorAll<HTMLElement>(FOCUSABLES));
      const premier = elements[0];
      const dernier = elements[elements.length - 1];
      if (e.shiftKey && (document.activeElement === premier || !panneau.current.contains(document.activeElement))) {
        e.preventDefault();
        dernier?.focus();
      } else if (!e.shiftKey && document.activeElement === dernier) {
        e.preventDefault();
        premier?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => bouton.current?.focus());
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      if (precedent?.isConnected) precedent.focus();
    };
  }, [ouverte, onFermer]);

  if (!monte) return null;

  return createPortal(
    <AnimatePresence>
      {ouverte && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
          <motion.div className="absolute inset-0 bg-black/50" onClick={onFermer} aria-hidden
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div ref={panneau} role="dialog" aria-modal="true" aria-labelledby="ouverture-titre" aria-describedby="ouverture-texte"
            initial={{ opacity: 0, scale: 0.96, y: 12 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="relative w-full max-w-md max-h-[92dvh] overflow-y-auto bg-white rounded-3xl shadow-card-hover px-6 sm:px-8 pt-9 pb-6 text-center">
            <button type="button" onClick={onFermer} aria-label={t("fermer")}
              className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center text-dark hover:bg-gray-100 focus-visible:!outline-accent">
              <X size={20} aria-hidden />
            </button>

            <span className="relative mx-auto w-[72px] h-[72px] rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
              <Home size={30} strokeWidth={1.75} aria-hidden />
              <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-accent text-white border-2 border-white flex items-center justify-center" aria-hidden>
                <Sparkle size={11} className="fill-white" />
              </span>
            </span>

            <h2 id="ouverture-titre" className="font-heading font-bold text-2xl sm:text-[28px] leading-tight text-dark mt-5">{t("titre")}</h2>
            <p id="ouverture-texte" className="text-sm sm:text-base text-gray-600 leading-relaxed mt-3">{t("texte")}</p>

            <button ref={bouton} type="button" onClick={onCreer}
              className="w-full mt-7 min-h-[52px] rounded-xl bg-primary text-white font-bold hover:bg-primary-600 focus-visible:!outline-accent">
              {t("creer")}
            </button>
            <button type="button" onClick={onFermer}
              className="w-full mt-3 min-h-[52px] rounded-xl bg-gray-100 text-dark font-bold hover:bg-gray-200 focus-visible:!outline-accent">
              {t("plusTard")}
            </button>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
