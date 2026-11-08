"use client";

import { accesEspaceHote, CLE_MOI, ouvrirCandidature, useMoi } from "@/features/users";
import { Link, useRouter } from "@/i18n/navigation";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useQueryClient } from "@tanstack/react-query";
import { Car, CheckCircle, Home, MessageCircle, Wallet } from "lucide-react";
import { CONTACT_EMAIL } from "@/lib/contact";
import { useReglagesSite } from "@/lib/site";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { useTranslations } from "next-intl";
import { useTaux } from "@/features/paiements";
import EstimateurRevenus from "./EstimateurRevenus";

const TAUX = ["particulier", "hotel", "fondateur", "voyageur"] as const;

const STEPS = [
  { icon: Home, id: "publier" },
  { icon: MessageCircle, id: "echanger" },
  { icon: Wallet, id: "recevoir" },
];

export default function DevenirHotePage() {
  const t = useTranslations("devenirHote");
  // Rates set in the back-office
  const { texte: texteTaux } = useTaux();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { status } = useSession();
  const { data: me } = useMoi(status === "authenticated");
  const [loading, setLoading] = useState(false);
  const acces = !!me && accesEspaceHote(me);
  const assistant = useReglagesSite().data?.modules.assistant_hote === true;

  // Coming back from sign-up: the account exists, the candidature starts with the button below.
  // Read from the address, not useSearchParams: this public page must stay rendered on the server
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("bienvenue") !== "1") return;
    toast.success(t("bienvenue"));
    router.replace("/hote");
  }, [router, t]);

  const commencer = async () => {
    setLoading(true);
    try {
      await ouvrirCandidature();
      await queryClient.invalidateQueries({ queryKey: CLE_MOI });
      toast.success(t("active"));
      router.push(assistant ? "/hote/annonce/nouvelle" : "/hote/espace");
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setLoading(false);
    }
  };

  const cta =
    status === "loading" || (status === "authenticated" && !me) ? null : acces ? (
      <Link href="/hote/espace" className="inline-block bg-white text-primary font-bold px-8 py-4 rounded-full shadow-lg hover:bg-gray-50">{t(me?.candidature_hote === "ouverte" ? "reprendre" : "acceder")}</Link>
    ) : me?.candidature_hote === "refusee" ? (
      <p className="max-w-xl mx-auto bg-white/10 rounded-2xl px-5 py-4 text-sm text-white">{t("refusee", { motif: me.candidature_motif })}</p>
    ) : status === "authenticated" ? (
      <button onClick={commencer} disabled={loading} className="bg-white text-primary font-bold px-8 py-4 rounded-full shadow-lg hover:bg-gray-50 disabled:opacity-60">
        {loading ? t("activation") : t("activer")}
      </button>
    ) : (
      <Link href="/register?role=hote" className="inline-block bg-white text-primary font-bold px-8 py-4 rounded-full shadow-lg hover:bg-gray-50">{t("creerCompte")}</Link>
    );

  return (
    <div className="bg-light">
      <section className="relative overflow-hidden bg-primary text-white">
        <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1613490493576-7fde63acd811?q=80&w=2000&auto=format&fit=crop')" }} />
        {/* The photo stays visible; the gradient keeps the text readable */}
        <div className="absolute inset-0 bg-gradient-to-t from-primary-900/95 via-primary-900/70 to-primary-900/40" />
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-24 text-center">
          <h1 className="font-heading font-bold text-3xl sm:text-4xl md:text-5xl mb-4 drop-shadow-sm selection:bg-white selection:text-primary">{t("titre")}</h1>
          <p className="text-white/90 text-base md:text-lg max-w-2xl mx-auto mb-8 selection:bg-white selection:text-primary">
            {t("sousTitre")}
          </p>
          {cta}
          {status === "unauthenticated" && (
            <p className="text-white/80 text-sm mt-4 selection:bg-white selection:text-primary">
              {t.rich("dejaInscrit", { lien: (x) => <Link href="/login?callbackUrl=/hote" className="font-bold underline">{x}</Link> })}
            </p>
          )}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-14 md:py-20">
        <h2 className="font-heading font-bold text-dark text-2xl md:text-3xl text-center mb-10">{t("commentCaMarche")}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {STEPS.map(({ icon: Icon, id }, i) => (
            <div key={id} className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-center gap-3 mb-4">
                <span className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center"><Icon size={20} /></span>
                <span className="text-sm font-bold text-muted">{t("etape", { numero: i + 1 })}</span>
              </div>
              <h3 className="font-heading font-bold text-dark text-lg mb-2">{t(`etapes.${id}.titre`)}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{t(`etapes.${id}.texte`)}</p>
            </div>
          ))}
        </div>

        <div className="mt-12">
          <h2 className="font-heading font-bold text-dark text-2xl md:text-3xl text-center mb-3">{t("tarifs.titre")}</h2>
          <p className="text-gray-500 text-center max-w-2xl mx-auto mb-8">{t("tarifs.intro")}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {TAUX.map((cle) => (
              <div key={cle} className="bg-white rounded-3xl p-5 border border-gray-100 text-center">
                <p className="font-heading font-bold text-primary text-3xl">{texteTaux[cle]}</p>
                <p className="font-semibold text-dark text-sm mt-1">{t(`tarifs.taux.${cle}.titre`)}</p>
                <p className="text-gray-500 text-xs mt-1 leading-relaxed">{t(`tarifs.taux.${cle}.texte`)}</p>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <h3 className="font-heading font-bold text-dark text-lg mb-1">{t("tarifs.estimateurTitre")}</h3>
            <p className="text-sm text-gray-500 mb-4">{t("tarifs.estimateurTexte")}</p>
            <EstimateurRevenus />
          </div>

          <div className="mt-6 bg-primary/5 rounded-3xl p-5 md:p-6 flex flex-col sm:flex-row gap-4 sm:items-center">
            <span className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><Car size={22} /></span>
            <div className="flex-1">
              <p className="font-heading font-bold text-dark">{t("tarifs.mobilite.titre")}</p>
              <p className="text-sm text-gray-600 mt-1 leading-relaxed">{t("tarifs.mobilite.texte")}</p>
            </div>
            <a href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(t("tarifs.mobilite.sujet"))}`} className="text-sm font-bold text-primary hover:underline whitespace-nowrap">{t("tarifs.mobilite.cta")}</a>
          </div>
        </div>

        <div className="mt-12 bg-white rounded-3xl p-6 md:p-8 border border-gray-100">
          <h3 className="font-heading font-bold text-dark text-lg mb-4">{t("ceQuIlFaut")}</h3>
          <ul className="grid sm:grid-cols-2 gap-3 text-sm text-gray-600">
            {["compte", "identite", "photos", "prix", "capacite"].map((cle) => t(`besoins.${cle}`)).map((item) => (
              <li key={item} className="flex items-start gap-2"><CheckCircle size={16} className="text-secondary flex-shrink-0 mt-0.5" />{item}</li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
