"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getSession, signIn } from "next-auth/react";
import { Mail, RefreshCw } from "lucide-react";
import { renvoyerCode } from "./api";
import AuthShell from "./AuthShell";
import { cn } from "@/lib/utils";
import { emailRetenu, oublierEmail, retenirEmail } from "@/lib/email-en-cours";
import { useTranslations } from "next-intl";

const EMPTY = ["", "", "", "", "", ""];

function VerifyForm() {
  const router = useRouter();
  const t = useTranslations("auth");
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [emailKnown, setEmailKnown] = useState(false);
  const [digits, setDigits] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const autoResent = useRef(false);

  const code = digits.join("");

  // sessionStorage only exists in the browser
  useEffect(() => {
    const stored = emailRetenu();
    if (stored) {
      setEmail(stored);
      setEmailKnown(true);
    }
    inputs.current[0]?.focus();
  }, []);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const handleSubmit = async (codeVal = code) => {
    if (codeVal.length !== 6 || loading || !email) return;
    setError("");
    setSuccess("");
    setLoading(true);

    // The code proves ownership of the address: the session opens without a password
    const res = await signIn("email-code", { redirect: false, email, code: codeVal }).catch(() => null);

    if (!res || res.error) {
      if (res?.code === "already_verified") {
        retenirEmail(email);
        router.push("/login?verified=1");
        return;
      }
      const messages: Record<string, string> = { too_many_attempts: t("tropDeTentatives"), serveur: t("serveurInjoignable") };
      setError(res ? (messages[res.code ?? ""] ?? t("codeInvalide")) : t("serveurInjoignable"));
      setDigits(EMPTY);
      inputs.current[0]?.focus();
      setLoading(false);
      return;
    }

    oublierEmail();
    const session = await getSession();
    router.push(session?.user.role === "hote" ? "/hote/espace?bienvenue=1" : "/?bienvenue=1");
    router.refresh();
  };

  const handleChange = (i: number, val: string) => {
    const clean = val.replace(/\D/g, "");
    if (clean.length > 1) {
      // Saisie automatique (SMS / gestionnaire) de plusieurs chiffres
      const next = clean.slice(0, 6).split("");
      const filled = [...next, ...EMPTY].slice(0, 6);
      setDigits(filled);
      inputs.current[Math.min(next.length, 5)]?.focus();
      if (next.length === 6) handleSubmit(next.join(""));
      return;
    }
    const next = [...digits];
    next[i] = clean;
    setDigits(next);
    if (clean && i < 5) inputs.current[i + 1]?.focus();
    if (next.join("").length === 6) handleSubmit(next.join(""));
  };

  const handleKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !digits[i] && i > 0) inputs.current[i - 1]?.focus();
    if (e.key === "ArrowLeft" && i > 0) inputs.current[i - 1]?.focus();
    if (e.key === "ArrowRight" && i < 5) inputs.current[i + 1]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) {
      e.preventDefault();
      setDigits(pasted.split(""));
      handleSubmit(pasted);
    }
  };

  const handleResend = async () => {
    if (!email || cooldown > 0) return;
    setResending(true);
    setError("");
    setSuccess("");
    try {
      const { status, data } = await renvoyerCode(email);
      if (status < 400) {
        setSuccess(t("codeRenvoye"));
        setCooldown(60);
      } else if (status === 429) {
        setCooldown(data.retry_after ?? 60);
        setError(data.detail ?? t("patienter"));
      } else if (data.code === "already_verified") {
        retenirEmail(email);
        router.push("/login?verified=1");
      } else {
        setError(data.detail ?? t("erreurEnvoi"));
      }
    } catch {
      setError(t("serveurInjoignable"));
    }
    setResending(false);
  };

  // Coming from the sign-in of an unverified account: a fresh code is sent
  useEffect(() => {
    if (searchParams.get("resend") === "1" && email && !autoResent.current) {
      autoResent.current = true;
      handleResend();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email]);

  return (
    <>
      <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center mb-6">
        <Mail size={26} className="text-primary" />
      </div>

      <h1 className="font-heading font-bold text-3xl text-dark mb-2">{t("verificationEmail")}</h1>

      {emailKnown ? (
        <>
          <p className="text-gray-500 text-sm mb-1">{t("saisirCode")}</p>
          <p className="font-semibold text-dark text-sm mb-8 break-all">{email}</p>
        </>
      ) : (
        <div className="mb-8">
          <label htmlFor="email" className="block text-gray-500 text-sm mb-2">{t("emailAVerifier")}</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value.trim().toLowerCase())}
            placeholder={t("emailExemple")}
            className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
      )}

      {error && (
        <div role="alert" className="p-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl text-center font-medium mb-6">{error}</div>
      )}
      {success && (
        <div role="status" className="p-3 text-sm text-green-700 bg-green-50 border border-green-100 rounded-xl text-center font-medium mb-6">{success}</div>
      )}

      <div className="flex gap-2 sm:gap-3 justify-center mb-8" onPaste={handlePaste}>
        {digits.map((d, i) => (
          <input
            key={i}
            ref={(el) => { inputs.current[i] = el; }}
            type="text"
            inputMode="numeric"
            autoComplete={i === 0 ? "one-time-code" : "off"}
            aria-label={t("chiffre", { numero: i + 1 })}
            maxLength={i === 0 ? 6 : 1}
            value={d}
            disabled={loading}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            onFocus={(e) => e.target.select()}
            className={cn(
              "w-11 h-14 sm:w-12 text-center text-xl font-bold border-2 rounded-xl outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20",
              d ? "border-primary bg-primary/5 text-primary" : "border-gray-200 text-dark"
            )}
          />
        ))}
      </div>

      <button
        onClick={() => handleSubmit()}
        disabled={loading || code.length !== 6 || !email}
        className="w-full bg-primary text-white font-bold py-4 rounded-xl shadow-button hover:shadow-lg transform hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:transform-none text-sm"
      >
        {loading ? t("verificationEnCours") : t("verifierMonCompte")}
      </button>

      <div className="mt-6 text-center">
        <p className="text-sm text-gray-500 mb-2">{t("pasRecuCode")}</p>
        <button
          onClick={handleResend}
          disabled={resending || cooldown > 0 || !email}
          className="inline-flex items-center gap-2 text-sm font-bold text-primary hover:underline disabled:opacity-50 disabled:no-underline"
        >
          <RefreshCw size={14} className={resending ? "animate-spin" : ""} />
          {resending ? t("envoiEnCours") : cooldown > 0 ? t("renvoyerCodeDans", { secondes: cooldown }) : t("renvoyerCode")}
        </button>
      </div>

      <p className="mt-6 text-center text-sm text-gray-500">
        {t("mauvaiseAdresse")}{" "}
        <Link href="/register" className="font-bold text-primary hover:underline">{t("recommencerInscription")}</Link>
      </p>
    </>
  );
}

export default function VerifyPage() {
  const t = useTranslations("auth");
  return (
    <AuthShell
      reverse
      image="/accueil/hero-7-mobile.jpg?v=2"
      title={t("verifierVisuelTitre")}
      subtitle={t("verifierVisuelTexte")}
    >
      <Suspense>
        <VerifyForm />
      </Suspense>
    </AuthShell>
  );
}
