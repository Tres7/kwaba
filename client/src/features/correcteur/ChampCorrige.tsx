"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { SpellCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCorrecteur } from "./hooks";
import { fauteA, morceaux, sansChoix } from "./texte";
import type { Faute } from "./types";

/** Mistakes listed under the field before « See the others » */
const MAX_AFFICHEES = 3;

// Properties copied from the field to the underlining layer: the text must wrap at exactly the same places
const PROPRIETES = [
  "font-family", "font-size", "font-weight", "font-style", "font-variant", "font-stretch", "line-height", "letter-spacing",
  "word-spacing", "text-transform", "text-indent", "text-align", "tab-size", "overflow-wrap", "word-break",
  "padding-top", "padding-right", "padding-bottom", "padding-left",
];

type Commun = {
  valeur: string;
  onValeur: (valeur: string) => void;
};
type Desactives = "value" | "defaultValue" | "onChange" | "onScroll" | "onSelect" | "spellCheck";
type PropsZone = Commun & { multiligne: true } & Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, Desactives>;
type PropsLigne = Commun & { multiligne?: false } & Omit<React.InputHTMLAttributes<HTMLInputElement>, Desactives>;
export type ChampCorrigeProps = PropsZone | PropsLigne;

/**
 * Text field that underlines spelling (red) and grammar (orange) mistakes, with their corrections under it.
 * Only an aid: nothing is blocked. The field keeps its own classes; the underlining layer is drawn over it, without
 * catching clicks.
 */
export default function ChampCorrige(props: ChampCorrigeProps) {
  const { valeur, onValeur, multiligne, className, ...reste } = props;
  const t = useTranslations("correcteur");
  const champ = useRef<HTMLTextAreaElement | HTMLInputElement | null>(null);
  const calque = useRef<HTMLDivElement>(null);
  const { disponible, fautes, corriger, toutCorriger, ignorer } = useCorrecteur(valeur);
  const [curseur, setCurseur] = useState<number | null>(null);
  const [toutVoir, setToutVoir] = useState(false);
  const active = fauteA(fautes, curseur);

  // Layer exactly over the text area of the field (inside its borders, without its scrollbar), at the same scroll
  useLayoutEffect(() => {
    const el = champ.current;
    const couche = calque.current;
    if (!el || !couche) return;
    const placer = () => {
      const style = getComputedStyle(el);
      for (const propriete of PROPRIETES) couche.style.setProperty(propriete, style.getPropertyValue(propriete));
      couche.style.top = `${el.offsetTop + el.clientTop}px`;
      couche.style.left = `${el.offsetLeft + el.clientLeft}px`;
      couche.style.width = `${el.clientWidth}px`;
      couche.style.height = `${el.clientHeight}px`;
      couche.scrollTop = el.scrollTop;
      couche.scrollLeft = el.scrollLeft;
    };
    placer();
    const observateur = new ResizeObserver(placer);
    observateur.observe(el);
    // Self-hosted fonts load after the first display: the widths of the letters change
    document.fonts?.ready.then(placer).catch(() => {});
    return () => observateur.disconnect();
  }, [multiligne]);

  // Same scroll after every change of the text (a one-line field scrolls by itself while typing)
  useLayoutEffect(() => {
    if (champ.current && calque.current) {
      calque.current.scrollTop = champ.current.scrollTop;
      calque.current.scrollLeft = champ.current.scrollLeft;
    }
  });

  const suivreCurseur = (e: React.SyntheticEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    setCurseur(e.currentTarget.selectionStart);
    if (calque.current) {
      calque.current.scrollTop = e.currentTarget.scrollTop;
      calque.current.scrollLeft = e.currentTarget.scrollLeft;
    }
  };
  const remplacer = (faute: Faute, remplacement: string) => {
    onValeur(corriger(faute, remplacement));
    setCurseur(null);
  };
  const montrer = (faute: Faute) => {
    const el = champ.current;
    if (!el) return;
    el.focus();
    el.setSelectionRange(faute.debut, faute.debut + faute.longueur);
    setCurseur(faute.debut);
  };

  const communs = {
    className,
    // Our checker replaces the browser's one, which often uses another language than the text
    spellCheck: disponible ? false : undefined,
    onSelect: suivreCurseur,
    onScroll: suivreCurseur,
  };
  const champRendu = multiligne ? (
    <textarea {...(reste as React.TextareaHTMLAttributes<HTMLTextAreaElement>)} {...communs} value={valeur}
      ref={(el) => { champ.current = el; }} onChange={(e) => onValeur(e.target.value)} />
  ) : (
    <input {...(reste as React.InputHTMLAttributes<HTMLInputElement>)} {...communs} value={valeur}
      ref={(el) => { champ.current = el; }} onChange={(e) => onValeur(e.target.value)} />
  );

  const ordre = active ? [active, ...fautes.filter((f) => f !== active)] : fautes;
  const affichees = toutVoir ? ordre : ordre.slice(0, MAX_AFFICHEES);
  const corrigeables = fautes.filter(sansChoix).length;

  return (
    <div>
      <div className="relative">
        {champRendu}
        <div ref={calque} aria-hidden
          className={cn("absolute box-border overflow-hidden pointer-events-none text-transparent", multiligne ? "whitespace-pre-wrap" : "whitespace-pre")}>
          {morceaux(valeur, fautes).map((m, i) => (m.faute ? (
            <span key={i} className={cn("underline decoration-wavy decoration-[1.5px] underline-offset-[3px] [text-decoration-skip-ink:none]",
              m.faute.type === "orthographe" ? "decoration-red-600" : "decoration-amber-500",
              m.faute === active && (m.faute.type === "orthographe" ? "bg-red-500/10" : "bg-amber-500/15"))}>{m.texte}</span>
          ) : m.texte))}
          {"\u200b"}
        </div>
      </div>

      {/* Announced by screen readers when the number changes; the list itself is not read again at each check */}
      <p className="sr-only" aria-live="polite">{fautes.length > 0 ? t("resume", { nombre: fautes.length }) : ""}</p>
      {fautes.length > 0 && (
        <div className="mt-2 rounded-2xl border border-gray-200 bg-white p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-sm font-semibold text-dark">
              <SpellCheck size={16} className="text-primary shrink-0" aria-hidden /> {t("resume", { nombre: fautes.length })}
            </p>
            {corrigeables > 1 && (
              <button type="button" onClick={() => { onValeur(toutCorriger()); setCurseur(null); }}
                className="text-sm font-semibold text-primary hover:underline min-h-9 px-1">
                {t("toutCorriger")}
              </button>
            )}
          </div>
          <ul className="mt-2 grid gap-1.5">
            {affichees.map((faute) => (
              <li key={`${faute.debut}-${faute.regle}`} className={cn("rounded-xl px-3 py-2.5", faute === active ? "bg-light" : "bg-gray-50")}>
                <p className="text-sm text-dark">
                  <button type="button" onClick={() => montrer(faute)} title={t("voirDansLeTexte")}
                    className={cn("font-semibold underline decoration-wavy underline-offset-[3px] [text-decoration-skip-ink:none]",
                      faute.type === "orthographe" ? "decoration-red-600" : "decoration-amber-500")}>
                    {faute.extrait.trim() ? faute.extrait : t("espaces")}
                  </button>
                  <span className="text-gray-600"> · {faute.type === "orthographe" ? t("orthographe") : faute.message || t("grammaire")}</span>
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {faute.remplacements.map((remplacement) => (
                    <button key={remplacement} type="button" onClick={() => remplacer(faute, remplacement)}
                      aria-label={remplacement.trim() ? t("remplacerPar", { mot: remplacement }) : t("corriger")}
                      className="min-h-9 px-3 rounded-full bg-primary-50 text-primary text-sm font-semibold hover:bg-primary-100 transition-colors">
                      {remplacement.trim() ? remplacement : t("corriger")}
                    </button>
                  ))}
                  <button type="button" onClick={() => ignorer(faute)}
                    className="min-h-9 px-3 rounded-full text-sm text-gray-600 hover:bg-gray-100 transition-colors">
                    {t("ignorer")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {ordre.length > MAX_AFFICHEES && (
            <button type="button" onClick={() => setToutVoir((v) => !v)} className="mt-2 text-sm font-semibold text-primary hover:underline min-h-9 px-1">
              {toutVoir ? t("voirMoins") : t("voirLesAutres", { nombre: ordre.length - MAX_AFFICHEES })}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
