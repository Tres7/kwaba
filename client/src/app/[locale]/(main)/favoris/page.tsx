"use client";

import { Link } from "@/i18n/navigation";
import { Heart, Search, ArrowLeft } from "lucide-react";
import PropertyCard from "@/components/hebergement/PropertyCard";
import { useFavoris, useOterDeLaListe } from "@/features/favoris";
import { useTranslations } from "next-intl";

export default function FavorisPage() {
  const t = useTranslations("mesFavoris");
  const { data: favoris = [], isLoading, isError, refetch } = useFavoris();
  const oterDeLaListe = useOterDeLaListe();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <div className="mb-8 flex items-center gap-4">
        <Link href="/profil" aria-label={t("retourProfil")} className="w-10 h-10 rounded-full bg-white shadow-sm flex items-center justify-center text-dark hover:bg-light-muted transition-colors flex-shrink-0">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">{t("titre")}</h1>
          <p className="text-muted text-sm mt-1">
            {favoris.length > 0 ? t("nombre", { nombre: favoris.length }) : t("sousTitre")}
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-72 skeleton rounded-2xl" />)}
        </div>
      ) : isError ? (
        <div className="bg-white rounded-3xl shadow-card p-12 text-center">
          <p className="text-dark font-semibold mb-2">{t("erreur")}</p>
          <button onClick={() => refetch()} className="text-primary font-bold hover:underline">{t("reessayer")}</button>
        </div>
      ) : favoris.length === 0 ? (
        <div className="bg-white rounded-3xl shadow-card p-8 sm:p-12 flex flex-col items-center gap-6 text-center">
          <div className="w-24 h-24 bg-primary/5 rounded-full flex items-center justify-center text-primary/50">
            <Heart size={40} />
          </div>
          <div className="max-w-sm">
            <h2 className="font-heading font-bold text-xl text-dark mb-2">{t("aucun")}</h2>
            <p className="text-muted text-sm mb-8 leading-relaxed">{t("aucunTexte")}</p>
            <Link href="/recherche" className="inline-flex items-center gap-2 bg-primary text-white font-medium px-8 py-3.5 rounded-xl shadow-md hover:bg-primary-600 transition-all">
              <Search size={18} /> {t("explorer")}
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {favoris.map((f) => (
            <PropertyCard
              key={f.id}
              property={{ ...f.hebergement_detail, is_favorite: true }}
              onFavoriteChange={(fav) => { if (!fav) oterDeLaListe(f.hebergement); }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
