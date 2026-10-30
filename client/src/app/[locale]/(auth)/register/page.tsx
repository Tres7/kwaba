"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Mail, Lock, User, Phone, Eye, EyeOff, Plane, Home } from "lucide-react";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { urlProxy } from "@/lib/api-url";
import { firstErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import AuthShell from "@/components/auth/AuthShell";
import GoogleButton from "@/components/auth/GoogleButton";
import Captcha, { type CaptchaHandle } from "@/components/auth/Captcha";
import FormField from "@/components/ui/FormField";
import { useLocale, useTranslations } from "next-intl";

type Role = "voyageur" | "hote";
type FieldErrors = Partial<Record<"email" | "first_name" | "last_name" | "phone" | "password" | "password_confirm" | "role", string>>;

const ROLES: { id: Role; label: string; icon: typeof Plane }[] = [
  { id: "voyageur", label: "voyageur", icon: Plane },
  { id: "hote", label: "hote", icon: Home },
];

function passwordStrength(pw: string): { score: number } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return { score };
}

function RegisterForm() {
  const router = useRouter();
  const t = useTranslations("auth");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const [role, setRole] = useState<Role>(searchParams.get("role") === "hote" ? "hote" : "voyageur");
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "", password: "", password_confirm: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [existingAccount, setExistingAccount] = useState(false);
  const [captcha, setCaptcha] = useState<string | null>(null);
  const [captchaRequis, setCaptchaRequis] = useState(false);
  // Button enabled once the page is ready (JavaScript loaded): an earlier click would send the form without it
  const [pret, setPret] = useState(false);
  useEffect(() => setPret(true), []);
  const captchaRef = useRef<CaptchaHandle>(null);

  const strength = passwordStrength(form.password);
  const mismatch = form.password_confirm.length > 0 && form.password !== form.password_confirm;

  const update = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    setExistingAccount(false);

    if (form.password.length < 8) {
      setFieldErrors({ password: t("mdpTropCourt") });
      return;
    }
    if (mismatch) {
      setFieldErrors({ password_confirm: t("mdpDifferents") });
      return;
    }
    if (captchaRequis && !captcha) {
      setError(t("captchaRequis"));
      return;
    }

    setLoading(true);
    const email = form.email.trim().toLowerCase();

    try {
      const res = await fetch(urlProxy("/v1/auth/register/"), {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept-Language": locale },
        body: JSON.stringify({ ...form, email, role, phone: form.phone.trim() || null, captcha: captcha ?? "" }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        // The captcha token can only be used once
        captchaRef.current?.reset();
        if ((data as { code?: string }).code === "captcha") {
          setError(t("captchaRequis"));
        } else if (res.status === 400 || res.status === 409) {
          const errs: FieldErrors = {};
          for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
            const msg = firstErrorMessage(value);
            if (msg) errs[key as keyof FieldErrors] = msg;
          }
          setFieldErrors(errs);
          if (res.status === 409 && errs.email) setExistingAccount(true);
          if (!Object.keys(errs).length) setError(firstErrorMessage(data) ?? t("donneesInvalides"));
        } else {
          setError(t("erreurServeur"));
        }
        setLoading(false);
        return;
      }
    } catch {
      setError(t("serveurInjoignable"));
      setLoading(false);
      return;
    }

    sessionStorage.setItem("verify_email", email);
    router.push(`/verify?email=${encodeURIComponent(email)}`);
  };

  return (
    <>
      <h1 className="font-heading font-bold text-3xl text-dark mb-2">{t("creerCompte")}</h1>
      <p className="text-gray-500 text-sm mb-8">{t("inscriptionTexte")}</p>

      <GoogleButton label={t("inscriptionGoogle")} callbackUrl="/" onError={setError} />

      <form method="post" className="space-y-4" onSubmit={handleSubmit}>
        {error && (
          <div role="alert" className="p-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl text-center font-medium">
            {error}
          </div>
        )}

        <fieldset>
          <legend className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">{t("jeSuis")}</legend>
          <div className="grid grid-cols-2 gap-2">
            {ROLES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setRole(id)}
                aria-pressed={role === id}
                className={cn(
                  "flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border transition-all",
                  role === id ? "bg-primary text-white border-primary shadow-button" : "bg-white text-dark border-gray-200 hover:border-primary/40"
                )}
              >
                <Icon size={15} /> {t(`roles.${label}`)}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-1.5 ml-1">
            {role === "hote" ? t("roleHoteTexte") : t("roleVoyageurTexte")}
          </p>
        </fieldset>

        <div className="grid grid-cols-1 min-[380px]:grid-cols-2 gap-3">
          <FormField label={t("prenom")} name="first_name" icon={User} value={form.first_name} onChange={update} placeholder="Ama" autoComplete="given-name" required error={fieldErrors.first_name} />
          <FormField label={t("nom")} name="last_name" icon={User} value={form.last_name} onChange={update} placeholder="Koffi" autoComplete="family-name" required error={fieldErrors.last_name} />
        </div>

        <div>
          <FormField label={t("email")} name="email" type="email" icon={Mail} value={form.email} onChange={update} placeholder={t("emailExemple")} autoComplete="email" inputMode="email" required error={fieldErrors.email} />
          {existingAccount && (
            <p className="text-xs text-gray-500 mt-1.5 ml-1">
              {t("cestVous")}{" "}
              <Link href={`/login?email=${encodeURIComponent(form.email)}`} className="text-primary font-bold hover:underline">{t("seConnecter")}</Link>
              {" "}{t("ou")}{" "}
              <Link href={`/verify?email=${encodeURIComponent(form.email.trim().toLowerCase())}`} className="text-primary font-bold hover:underline">{t("verifierCompte")}</Link>
            </p>
          )}
        </div>

        <FormField
          label={<>{t("telephone")} <span className="text-gray-400 normal-case font-normal">({t("optionnel")})</span></>}
          name="phone" type="tel" icon={Phone} value={form.phone} onChange={update}
          placeholder="+228 90 00 00 00" autoComplete="tel" inputMode="tel"
          hint={t("telephoneAide")}
          error={fieldErrors.phone}
        />

        <div>
          <FormField
            label={t("motDePasse")} name="password" type={showPassword ? "text" : "password"} icon={Lock}
            value={form.password} onChange={update} placeholder="••••••••" autoComplete="new-password" required
            error={fieldErrors.password}
            trailing={
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="relative zone-tactile p-1 text-gray-400 hover:text-dark" aria-label={showPassword ? t("masquerMdp") : t("afficherMdp")}>
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            }
          />
          {form.password && !fieldErrors.password && (
            <div className="mt-2 ml-1">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className={cn("h-1 flex-1 rounded-full", i <= strength.score ? (strength.score <= 2 ? "bg-red-400" : strength.score === 3 ? "bg-amber-400" : "bg-green-500") : "bg-gray-200")} />
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-1">{t(`force.${strength.score}`)}, {t("forceConseil")}</p>
            </div>
          )}
        </div>

        <FormField
          label={t("confirmerMdp")} name="password_confirm" type={showPassword ? "text" : "password"} icon={Lock}
          value={form.password_confirm} onChange={update} placeholder="••••••••" autoComplete="new-password" required
          error={fieldErrors.password_confirm ?? (mismatch ? t("mdpDifferents") : undefined)}
        />

        <div className="flex items-start gap-2 pt-1">
          <input type="checkbox" id="terms" className="mt-1 accent-primary w-4 h-4 flex-shrink-0" required />
          <label htmlFor="terms" className="text-xs text-gray-600 leading-relaxed">
            {t.rich("accepteCgu", {
              lien: (texte) => (
                <Link href="/cgu" target="_blank" className="text-primary font-medium underline">
                  {texte}<span className="sr-only"> ({t("nouvelOnglet")})</span>
                </Link>
              ),
            })}
          </label>
        </div>

        {/* GDPR notice: the account relies on the contract (terms of use), not on a consent box to tick */}
        <p className="text-xs text-gray-600 leading-relaxed bg-gray-50 rounded-xl p-3">
          {t("rgpd")}{" "}
          <Link href="/confidentialite" target="_blank" className="text-primary font-medium underline">
            {t("politiqueConfidentialite")}<span className="sr-only"> ({t("nouvelOnglet")})</span>
          </Link>
        </p>

        <Captcha ref={captchaRef} onToken={setCaptcha} onActif={() => setCaptchaRequis(true)} />

        <button
          type="submit"
          disabled={loading || !pret}
          className="w-full bg-primary text-white font-bold py-4 rounded-xl shadow-button hover:shadow-lg transform hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:transform-none text-sm mt-2"
        >
          {loading ? t("creationEnCours") : t("creerMonCompte")}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-500">
        {t("dejaUnCompte")}{" "}
        <Link href="/login" className="relative zone-tactile font-bold text-primary hover:underline">{t("seConnecter")}</Link>
      </p>
    </>
  );
}

export default function RegisterPage() {
  const t = useTranslations("auth");
  return (
    <AuthShell
      reverse
      image="/accueil/hero-7-mobile.jpg?v=2"
      title={t("inscriptionVisuelTitre")}
      subtitle={t("inscriptionVisuelTexte")}
    >
      <Suspense>
        <RegisterForm />
      </Suspense>
    </AuthShell>
  );
}
