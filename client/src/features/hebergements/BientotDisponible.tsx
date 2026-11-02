"use client";

import { sInscrireOuverture } from "./api";
import { useAucunLogement } from "./hooks";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { AnimatePresence, motion } from "framer-motion";
import { Car, CheckCircle2, HandHeart, Home, Loader2, Plane, X } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { apiErrorMessage } from "@/lib/api";
import { EVENEMENT, lireConsentement } from "@/lib/consentement";
import { filtrerLiens, useReglagesSite } from "@/lib/site";
import { useFormat } from "@/lib/format";

// Old key that kept the window from coming back: cleared from the browsers that still have it
const ANCIENNE_CLE = "kwaba_bientot_ferme";
// Lets the animated splash screen (2 s) go by before opening the window
const DELAI_MS = 2400;
// Pages where the window would get in the way: becoming a host, signing a contract
const PAGES_EXCLUES = /^\/(en\/)?(hote|contrat)(\/|$)/;
const CLE_VUE = "kwaba_bientot_vue";
const CLE_FERMEE = "kwaba_bientot_fermee";
const CLE_INSCRIT = "kwaba_bientot_inscrit";
const PAUSE_APRES_FERMETURE_MS = 7 * 24 * 60 * 60_000;

function doitAfficher(): boolean {
  try {
    if (window.sessionStorage.getItem(CLE_VUE) === "1") return false;
    if (window.localStorage.getItem(CLE_INSCRIT) === "1") return false;
    const fermee = Number(window.localStorage.getItem(CLE_FERMEE));
    return !fermee || Date.now() - fermee >= PAUSE_APRES_FERMETURE_MS;
  } catch {
    return true;
  }
}

function memoriser(stockage: "sessionStorage" | "localStorage", cle: string, valeur: string) {
  try {
    window[stockage].setItem(cle, valeur);
  } catch {
    return;
  }
}

/** "Notify me" form: the email is only used to announce the opening. */
export function PrevenezMoi({ compact }: { compact?: boolean }) {
  const { langue } = useFormat();
  const t = useTranslations("bientot");
  const [email, setEmail] = useState("");
  const [etat, setEtat] = useState<"saisie" | "envoi" | "ok">("saisie");
  const [erreur, setErreur] = useState("");

  const envoyer = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur("");
    setEtat("envoi");
    try {
      await sInscrireOuverture(email.trim(), langue());
      memoriser("localStorage", CLE_INSCRIT, "1");
      setEtat("ok");
    } catch (err) {
      setErreur(apiErrorMessage(err, t("erreur")));
      setEtat("saisie");
    }
  };

  if (etat === "ok") {
    return (
      <p role="status" className="flex items-start gap-2 text-sm text-dark bg-green-50 border border-green-100 rounded-xl px-4 py-3">
        <CheckCircle2 size={18} className="text-green-600 flex-shrink-0 mt-px" aria-hidden /> {t("merci")}
      </p>
    );
  }
  return (
    <form method="post" onSubmit={envoyer}>
      <label htmlFor={compact ? "bientot-email-bandeau" : "bientot-email"} className="sr-only">{t("email")}</label>
      <div className="flex flex-col sm:flex-row gap-2">
        <input id={compact ? "bientot-email-bandeau" : "bientot-email"} type="email" required autoComplete="email" value={email}
          onChange={(e) => setEmail(e.target.value)} placeholder={t("email")}
          className="flex-1 min-w-0 px-4 py-3 bg-white border border-gray-200 rounded-xl text-base sm:text-sm text-dark focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
        <button type="submit" disabled={etat === "envoi"}
          className="inline-flex items-center justify-center gap-2 min-h-[48px] px-5 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary-600 disabled:opacity-60 whitespace-nowrap">
          {etat === "envoi" && <Loader2 size={16} className="animate-spin" aria-hidden />} {t("prevenir")}
        </button>
      </div>
      {erreur && <p role="alert" className="text-xs text-red-600 mt-1.5">{erreur}</p>}
      {!compact && <p className="text-xs text-gray-500 mt-2">{t("rgpd")}</p>}
    </form>
  );
}

/** Window shown while the site has no published listing: once per browsing session, not again for 7 days
 * after being closed, and never again once the visitor has subscribed to the opening announcement. */
export default function BientotDisponible() {
  const t = useTranslations("bientot");
  const pathname = usePathname();
  const aucunLogement = useAucunLogement();
  const { data: reglages, isFetched: reglagesLus } = useReglagesSite();
  const modules = reglages?.modules;
  const banniereCookies = !!reglages?.mesure_audience;
  const [ouverte, setOuverte] = useState(false);
  // Client-side rendering only (portal): no mismatch with the server HTML
  const [monte, setMonte] = useState(false);
  useEffect(() => setMonte(true), []);
  const panneau = useRef<HTMLDivElement>(null);
  const exclue = PAGES_EXCLUES.test(pathname);
  const montree = useRef(false);

  useEffect(() => {
    try {
      window.localStorage.removeItem(ANCIENNE_CLE);
    } catch { /* stockage indisponible */ }
  }, []);

  // After the cookie choice (the consent banner comes first) and the splash screen
  useEffect(() => {
    if (!reglagesLus || !aucunLogement || exclue || montree.current || !doitAfficher()) return;
    let minuteur: ReturnType<typeof setTimeout> | undefined;
    const planifier = () => {
      minuteur = setTimeout(() => {
        montree.current = true;
        memoriser("sessionStorage", CLE_VUE, "1");
        setOuverte(true);
      }, DELAI_MS);
    };
    if (!banniereCookies || lireConsentement()) planifier();
    else window.addEventListener(EVENEMENT, planifier, { once: true });
    return () => {
      clearTimeout(minuteur);
      window.removeEventListener(EVENEMENT, planifier);
    };
  }, [reglagesLus, banniereCookies, aucunLogement, exclue]);

  const fermer = useCallback(() => {
    memoriser("localStorage", CLE_FERMEE, String(Date.now()));
    setOuverte(false);
  }, []);

  useEffect(() => {
    if (!ouverte) return;
    const precedent = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && fermer();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => panneau.current?.querySelector<HTMLElement>("input")?.focus());
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      precedent?.focus();
    };
  }, [ouverte, fermer]);

  if (!monte) return null;
  const services = [
    { href: "/transfert", icone: Plane, libelle: t("transfert") },
    { href: "/location", icone: Car, libelle: t("location") },
    { href: "/give", icone: HandHeart, libelle: t("give") },
  ].filter((s) => filtrerLiens([s], modules).length > 0);

  return createPortal(
    <AnimatePresence>
      {ouverte && (
        <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center sm:p-4">
          <motion.div className="absolute inset-0 bg-black/50" onClick={fermer} aria-hidden
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div ref={panneau} role="dialog" aria-modal="true" aria-labelledby="bientot-titre" aria-describedby="bientot-texte"
            initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 40 }} transition={{ duration: 0.25, ease: "easeOut" }}
            className="relative w-full sm:max-w-md max-h-[92dvh] overflow-y-auto bg-white rounded-t-3xl sm:rounded-3xl shadow-card-hover">
            <div className="relative bg-gradient-to-br from-primary to-primary-600 text-white px-6 pt-8 pb-7 text-center">
              <button type="button" onClick={fermer} aria-label={t("fermer")}
                className="absolute top-3 right-3 w-10 h-10 rounded-full flex items-center justify-center text-white/90 hover:bg-white/15">
                <X size={20} aria-hidden />
              </button>
              <span className="mx-auto w-14 h-14 rounded-2xl bg-white/15 flex items-center justify-center"><Home size={28} aria-hidden /></span>
              <p className="mt-4 text-xs font-bold uppercase tracking-wider text-white/80">{t("surtitre")}</p>
              <h2 id="bientot-titre" className="font-heading font-bold text-2xl mt-1">{t("titre")}</h2>
            </div>
            <div className="px-6 py-6 space-y-5">
              <p id="bientot-texte" className="text-sm text-gray-600 leading-relaxed">{t("texte")}</p>
              <PrevenezMoi />
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-dark mb-2">{t("enAttendant")}</p>
                <ul className="grid grid-cols-3 gap-2">
                  {services.map(({ href, icone: Icone, libelle }) => (
                    <li key={href}>
                      <Link href={href} onClick={fermer}
                        className="flex flex-col items-center gap-1.5 min-h-[76px] justify-center rounded-2xl border border-gray-100 bg-light px-2 py-3 text-center text-xs font-semibold text-dark hover:border-primary hover:text-primary transition-colors">
                        <Icone size={20} className="text-primary" aria-hidden /> {libelle}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-sm text-center text-gray-600">
                {t("proprietaire")}{" "}
                <Link href="/hote" onClick={fermer} className="font-bold text-primary underline">{t("devenirHote")}</Link>
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

/** Banner of the search pages while no listing is published. */
export function BandeauBientot() {
  const t = useTranslations("bientot");
  const aucunLogement = useAucunLogement();
  if (!aucunLogement) return null;
  return (
    <section aria-labelledby="bandeau-bientot" className="bg-white border border-primary/15 rounded-3xl p-5 sm:p-6 shadow-sm">
      <div className="flex items-start gap-4">
        <span className="w-11 h-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Home size={22} aria-hidden /></span>
        <div className="flex-1 min-w-0 space-y-3">
          <div>
            <h2 id="bandeau-bientot" className="font-heading font-bold text-dark text-lg">{t("titre")}</h2>
            <p className="text-sm text-gray-600 mt-1">{t("texte")}</p>
          </div>
          <PrevenezMoi compact />
        </div>
      </div>
    </section>
  );
}
