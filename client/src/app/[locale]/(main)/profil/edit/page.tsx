"use client";

import { Link } from "@/i18n/navigation";
import { ArrowLeft, User, Mail, Phone, Save } from "lucide-react";
import { useState, useEffect } from "react";
import { signOut, useSession } from "next-auth/react";
import { useQueryClient } from "@tanstack/react-query";
import api, { apiErrorMessage } from "@/lib/api";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import { useLocale, useTranslations } from "next-intl";

export default function EditProfilePage() {
  const t = useTranslations("profilEdition");
  const locale = useLocale();
  const { update } = useSession();
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
  });

  useEffect(() => {
    api.get("/v1/users/me/")
      .then((res) => {
        setForm({
          first_name: res.data.first_name ?? "",
          last_name: res.data.last_name ?? "",
          email: res.data.email ?? "",
          phone: res.data.phone ?? "",
        });
      })
      .catch(() => setError(t("erreurChargement")))
      .finally(() => setFetching(false));
    // Single load when the page opens
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      const res = await api.patch("/v1/users/me/", {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim() || null,
      });
      setForm((prev) => ({ ...prev, phone: res.data.phone ?? "" }));
      await update({ name: `${res.data.first_name} ${res.data.last_name}` });
      queryClient.invalidateQueries({ queryKey: ["me"] });
      setSuccess(true);
    } catch (err) {
      setError(apiErrorMessage(err, t("erreurMaj")));
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="min-h-screen bg-light flex items-center justify-center">
        <p className="text-muted">{t("chargement")}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <div className="mb-8 flex items-center gap-4">
        <Link
          href="/profil"
          aria-label={t("retourProfil")}
          className="w-10 h-10 rounded-full bg-white shadow-sm flex items-center justify-center text-dark hover:bg-light transition-colors"
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">{t("titre")}</h1>
          <p className="text-muted text-sm mt-1">{t("sousTitre")}</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-5 sm:p-8 md:p-10">
        <form method="post" onSubmit={handleSubmit} className="space-y-6 max-w-lg">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl px-4 py-3 text-sm">
              {t("succes")}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-dark mb-1.5 ml-1">{t("prenom")}</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <User size={18} className="text-muted" />
                </div>
                <input
                  type="text"
                  name="first_name"
                  value={form.first_name}
                  onChange={handleChange}
                  className="w-full pl-11 pr-4 py-3 bg-light-muted border border-transparent rounded-xl text-base sm:text-sm text-dark focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all shadow-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-dark mb-1.5 ml-1">{t("nom")}</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <User size={18} className="text-muted" />
                </div>
                <input
                  type="text"
                  name="last_name"
                  value={form.last_name}
                  onChange={handleChange}
                  className="w-full pl-11 pr-4 py-3 bg-light-muted border border-transparent rounded-xl text-base sm:text-sm text-dark focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all shadow-sm"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-dark mb-1.5 ml-1">{t("email")}</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Mail size={18} className="text-muted" />
              </div>
              <input
                type="email"
                value={form.email}
                disabled
                className="w-full pl-11 pr-4 py-3 bg-light-muted border border-transparent rounded-xl text-muted cursor-not-allowed shadow-sm"
              />
            </div>
            <p className="text-xs text-muted ml-1 mt-1">{t("emailFixe")}</p>
          </div>

          <div>
            <label className="block text-sm font-semibold text-dark mb-1.5 ml-1">{t("telephone")}</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Phone size={18} className="text-muted" />
              </div>
              <input
                type="tel"
                name="phone"
                value={form.phone}
                onChange={handleChange}
                placeholder="+228 90 00 00 00"
                className="w-full pl-11 pr-4 py-3 bg-light-muted border border-transparent rounded-xl text-base sm:text-sm text-dark focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all shadow-sm"
              />
            </div>
          </div>

          <div className="pt-4 flex flex-col-reverse sm:flex-row sm:justify-end gap-3 border-t border-gray-100 mt-8">
            <Link
              href="/profil"
              className="px-6 py-3 rounded-xl border border-gray-200 text-dark font-medium text-center hover:bg-light-muted transition-colors"
            >
              Annuler
            </Link>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-2 px-8 py-3 bg-primary text-white rounded-xl font-medium shadow-md hover:bg-primary-600 hover:shadow-lg transition-all disabled:opacity-70"
            >
              <Save size={18} />
              {loading ? t("enregistrement") : t("enregistrer")}
            </button>
          </div>
        </form>
      </div>

      <section aria-labelledby="fermer-titre" className="mt-8 bg-white rounded-2xl border border-red-100 p-6 md:p-8">
        <h2 id="fermer-titre" className="font-heading font-bold text-lg text-dark">{t("fermerCompte")}</h2>
        <p className="text-sm text-gray-600 mt-2 max-w-2xl">
          {t.rich("fermerTexte", { lien: (x) => <Link href="/confidentialite#droits" className="text-primary underline">{x}</Link> })}
        </p>
        <button
          type="button"
          onClick={() => setConfirmation({
            titre: t("fermerConfirmTitre"),
            message: t("fermerConfirmTexte"),
            libelle: t("fermerCompte"),
            danger: true,
            action: async () => {
              try {
                await api.delete("/v1/users/me/");
                await signOut({ callbackUrl: `${locale === "en" ? "/en" : "/"}?compte=ferme` });
              } catch (err) {
                setError(apiErrorMessage(err, t("erreurFermeture")));
                throw err;
              }
            },
          })}
          className="mt-4 px-5 py-3 rounded-xl border-2 border-red-600 text-red-700 text-sm font-bold hover:bg-red-50"
        >
          {t("fermerCompte")}
        </button>
      </section>
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}
