"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Mail, Lock, Eye, EyeOff } from "lucide-react";
import { Suspense, useEffect, useRef, useState } from "react";
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import AuthShell from "@/components/auth/AuthShell";
import GoogleButton from "@/components/auth/GoogleButton";
import Captcha, { type CaptchaHandle } from "@/components/auth/Captcha";
import FormField from "@/components/ui/FormField";
import { safeCallback } from "@/lib/redirection";
import { emailRetenu, oublierEmail, retenirEmail } from "@/lib/email-en-cours";
import { useTranslations } from "next-intl";

function LoginForm() {
  const router = useRouter();
  const t = useTranslations("auth");
  const searchParams = useSearchParams();
  const callbackUrl = safeCallback(searchParams.get("callbackUrl"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [unverified, setUnverified] = useState(false);
  const [captcha, setCaptcha] = useState<string | null>(null);
  const [captchaRequis, setCaptchaRequis] = useState(false);
  // Button enabled once the page is ready (JavaScript loaded): an earlier click would send the form without it
  const [pret, setPret] = useState(false);
  useEffect(() => {
    setPret(true);
    setEmail((actuel) => actuel || emailRetenu());
  }, []);
  const captchaRef = useRef<CaptchaHandle>(null);

  const notice =
    searchParams.get("verified") === "1"
      ? t("noticeVerifie")
      : searchParams.get("reset") === "1"
        ? t("noticeReset")
        : searchParams.get("expired") === "1"
          ? t("noticeExpire")
          : "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Button always enabled: we explain rather than greying it out with no visible reason
    if (captchaRequis && !captcha) {
      setError(t("captchaRequis"));
      return;
    }
    setLoading(true);
    setError("");
    setUnverified(false);

    const res = await signIn("credentials", {
      redirect: false,
      email: email.trim().toLowerCase(),
      password,
      captcha: captcha ?? "",
    });

    if (res?.error) {
      // The captcha token can only be used once
      captchaRef.current?.reset();
      if (res.code === "captcha") {
        setError(t("captchaRequis"));
      } else if (res.code === "unverified_email") {
        setUnverified(true);
        setError(t("nonVerifie"));
      } else if (res.code === "inactive") {
        setError(t("desactive"));
      } else if (res.code === "too_many_attempts") {
        setError(t("tropDeTentatives"));
      } else if (res.code === "serveur") {
        setError(t("serveurInjoignable"));
      } else {
        setError(t("identifiantsIncorrects"));
      }
      setLoading(false);
      return;
    }

    oublierEmail();
    router.push(callbackUrl);
    router.refresh();
  };

  return (
    <>
      <h1 className="font-heading font-bold text-3xl text-dark mb-2">{t("connexion")}</h1>
      <p className="text-gray-500 text-sm mb-8">{t("connexionTexte")}</p>

      {notice && (
        <div role="status" className="p-3 mb-6 text-sm text-green-700 bg-green-50 border border-green-100 rounded-xl text-center font-medium">
          {notice}
        </div>
      )}

      <GoogleButton label={t("continuerGoogle")} callbackUrl={callbackUrl} onError={setError} />

      <form method="post" className="space-y-5" onSubmit={handleSubmit}>
        {error && (
          <div role="alert" className="p-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl text-center font-medium">
            {error}
            {unverified && (
              <>
                {" "}
                <Link href="/verify?resend=1" onClick={() => retenirEmail(email.trim().toLowerCase())} className="underline font-bold">
                  {t("verifierMaintenant")}
                </Link>
              </>
            )}
          </div>
        )}

        <FormField
          label={t("email")} name="email" type="email" icon={Mail}
          value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailExemple")} autoComplete="email" inputMode="email" required
        />

        <div>
          <FormField
            label={t("motDePasse")} name="password" type={showPassword ? "text" : "password"} icon={Lock}
            value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••" autoComplete="current-password" required
            trailing={
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="relative zone-tactile p-1 text-gray-400 hover:text-dark" aria-label={showPassword ? t("masquerMdp") : t("afficherMdp")}>
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            }
          />
          <div className="text-right mt-2">
            <Link href={`/mot-de-passe-oublie${email ? `?email=${encodeURIComponent(email)}` : ""}`} className="relative zone-tactile text-xs text-primary font-medium hover:underline">
              {t("mdpOublie")}
            </Link>
          </div>
        </div>

        <Captcha ref={captchaRef} onToken={setCaptcha} onActif={() => setCaptchaRequis(true)} />

        <button
          type="submit"
          disabled={loading || !pret}
          className="w-full bg-primary text-white font-bold py-4 rounded-xl shadow-button hover:shadow-lg transform hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:transform-none text-sm"
        >
          {loading ? t("connexionEnCours") : t("seConnecter")}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-500">
        {t("pasDeCompte")}{" "}
        <Link href="/register" className="relative zone-tactile font-bold text-primary hover:underline">{t("creerCompte")}</Link>
      </p>
    </>
  );
}

export default function LoginPage() {
  const t = useTranslations("auth");
  return (
    <AuthShell
      image="/accueil/hero-6-mobile.jpg?v=2"
      title={t("connexionVisuelTitre")}
      subtitle={t("connexionVisuelTexte")}
    >
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
