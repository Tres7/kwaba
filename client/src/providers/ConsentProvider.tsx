"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "@/i18n/navigation";
import { Cookie, X } from "lucide-react";
import { enregistrerConsentement, EVENEMENT, lireConsentement, type Consentement } from "@/lib/consentement";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface ContexteConsentement {
  consentement: Consentement | null;
  /** true once the storage is read (avoids showing the banner then removing it) */
  pret: boolean;
  definir: (contenusTiers: boolean) => void;
  ouvrirPreferences: () => void;
}

const Contexte = createContext<ContexteConsentement | null>(null);

export function useConsentement() {
  const c = useContext(Contexte);
  if (!c) throw new Error("useConsentement doit être utilisé dans ConsentProvider");
  return c;
}

function Interrupteur({ actif, onChange, desactive, id }: { actif: boolean; onChange?: (v: boolean) => void; desactive?: boolean; id: string }) {
  const t = useTranslations("cookies");
  return (
    <button
      id={id} type="button" role="switch" aria-checked={actif} disabled={desactive}
      onClick={() => onChange?.(!actif)}
      className={cn("relative w-12 h-7 rounded-full transition-colors flex-shrink-0 disabled:cursor-not-allowed", actif ? "bg-secondary" : "bg-gray-400")}
    >
      <span className={cn("absolute top-1 left-1 w-5 h-5 rounded-full bg-white shadow transition-transform", actif && "translate-x-5")} />
      <span className="sr-only">{actif ? t("active") : t("desactive")}</span>
    </button>
  );
}

function Preferences({ initial, onFermer, onEnregistrer }: { initial: boolean; onFermer: () => void; onEnregistrer: (v: boolean) => void }) {
  const [tiers, setTiers] = useState(initial);
  const t = useTranslations("cookies");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onFermer(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onFermer]);

  return createPortal(
    <div className="fixed inset-0 z-[110] flex items-end sm:items-center justify-center sm:p-6">
      <div className="absolute inset-0 bg-black/50" onClick={onFermer} aria-hidden />
      <div role="dialog" aria-modal="true" aria-labelledby="pref-titre" className="relative w-full sm:max-w-lg max-h-[90vh] overflow-auto bg-white rounded-t-3xl sm:rounded-3xl p-6 shadow-card-hover">
        <div className="flex items-start justify-between gap-4">
          <h2 id="pref-titre" className="font-heading font-bold text-dark text-xl">{t("parametres")}</h2>
          <button type="button" onClick={onFermer} aria-label={t("fermerSansEnregistrer")} className="w-9 h-9 -mr-2 -mt-1 rounded-full flex items-center justify-center hover:bg-gray-100" autoFocus>
            <X size={18} />
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          {t("modifierAToutMoment")}
        </p>

        <div className="mt-5 space-y-4">
          <div className="flex items-start justify-between gap-4 p-4 rounded-2xl bg-gray-50">
            <div>
              <label htmlFor="cookie-necessaires" className="font-semibold text-dark text-sm">{t("necessaires")}</label>
              <p className="text-xs text-gray-600 mt-1">{t("necessairesTexte")}</p>
            </div>
            <Interrupteur id="cookie-necessaires" actif desactive />
          </div>
          <div className="flex items-start justify-between gap-4 p-4 rounded-2xl border border-gray-200">
            <div>
              <label htmlFor="cookie-tiers" className="font-semibold text-dark text-sm">{t("tiers")}</label>
              <p className="text-xs text-gray-600 mt-1">{t("tiersTexte")}</p>
            </div>
            <Interrupteur id="cookie-tiers" actif={tiers} onChange={setTiers} />
          </div>
        </div>

        <p className="text-xs text-gray-600 mt-4">{t("aucuneMesure")}</p>

        <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-2 mt-6">
          <Link href="/cookies" onClick={onFermer} className="text-sm font-semibold text-primary underline self-center">{t("politique")}</Link>
          <button type="button" onClick={() => onEnregistrer(tiers)} className="px-5 py-3 rounded-xl bg-dark text-white text-sm font-bold">{t("enregistrer")}</button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default function ConsentProvider({ children }: { children: React.ReactNode }) {
  const [consentement, setConsentement] = useState<Consentement | null>(null);
  const [pret, setPret] = useState(false);
  const [preferences, setPreferences] = useState(false);
  const t = useTranslations("cookies");

  useEffect(() => {
    setConsentement(lireConsentement());
    setPret(true);
    // Syncs the components (and the other tabs) when the choice changes
    const maj = () => setConsentement(lireConsentement());
    window.addEventListener(EVENEMENT, maj);
    window.addEventListener("storage", maj);
    return () => {
      window.removeEventListener(EVENEMENT, maj);
      window.removeEventListener("storage", maj);
    };
  }, []);

  const definir = useCallback((contenusTiers: boolean) => {
    setConsentement(enregistrerConsentement(contenusTiers));
    setPreferences(false);
  }, []);

  const ouvrirPreferences = useCallback(() => setPreferences(true), []);

  return (
    <Contexte.Provider value={{ consentement, pret, definir, ouvrirPreferences }}>
      {children}

      {pret && !consentement && !preferences && (
        <section
          role="region" aria-label={t("choix")}
          className="fixed z-[105] inset-x-3 bottom-3 sm:inset-x-auto sm:left-4 sm:bottom-4 sm:max-w-md bg-white rounded-3xl shadow-card-hover border border-gray-100 p-5"
        >
          <div className="flex items-start gap-3">
            <Cookie size={22} className="text-primary flex-shrink-0 mt-0.5" aria-hidden />
            <div>
              <h2 className="font-heading font-bold text-dark">{t("vosChoix")}</h2>
              <p className="text-sm text-gray-600 mt-1">
                {t("bandeau")}{" "}
                <Link href="/cookies" className="text-primary font-semibold underline">{t("enSavoirPlus")}</Link>
              </p>
            </div>
          </div>
          {/* Refusing is as easy as accepting: same size, same reading level (CNIL) */}
          <div className="grid grid-cols-2 gap-2 mt-4">
            <button type="button" onClick={() => definir(false)} className="py-3 rounded-xl border-2 border-dark text-dark text-sm font-bold hover:bg-gray-50">{t("toutRefuser")}</button>
            <button type="button" onClick={() => definir(true)} className="py-3 rounded-xl border-2 border-dark bg-dark text-white text-sm font-bold hover:bg-black">{t("toutAccepter")}</button>
          </div>
          <button type="button" onClick={ouvrirPreferences} className="w-full mt-2 py-2 text-sm font-semibold text-dark underline">{t("personnaliser")}</button>
        </section>
      )}

      {preferences && (
        <Preferences initial={consentement?.contenusTiers ?? false} onFermer={() => setPreferences(false)} onEnregistrer={definir} />
      )}
    </Contexte.Provider>
  );
}
