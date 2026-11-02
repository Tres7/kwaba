"use client";

import { lireStatsAdmin } from "@/features/users";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, CalendarCheck, ChevronRight, Home, IdCard, Star, Users } from "lucide-react";
import { useCompteursVerification } from "@/features/verifications";
import { formatPrice } from "@/lib/utils";
import CarteLancement from "@/features/hebergements/admin/CarteLancement";
import ReservationsChart from "@/components/backoffice/ReservationsChart";

function Tuile({ titre, valeur, detail, icone: Icone, href }: { titre: string; valeur: string; detail: string; icone: typeof Users; href: string }) {
  return (
    <Link href={href} className="block min-w-0 bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-card transition-shadow">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted font-medium">{titre}</p>
        <Icone size={18} className="text-gray-400" />
      </div>
      <p className="font-heading font-bold text-dark text-2xl sm:text-3xl mt-2 tabular-nums truncate">{valeur}</p>
      <p className="text-xs text-muted mt-1">{detail}</p>
    </Link>
  );
}

export default function TableauDeBord() {
  const { data: s, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: lireStatsAdmin,
  });
  // Same query as the menu badge (shared cache): refreshed every minute
  const { data: compteurs } = useCompteursVerification(true);
  const pieces = compteurs?.pieces ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Tableau de bord</h1>
        <p className="text-muted text-sm mt-1">Vue d&apos;ensemble de la plateforme.</p>
      </div>

      <CarteLancement />

      {isError ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
          <p className="text-dark font-semibold mb-2">Statistiques indisponibles.</p>
          <button onClick={() => refetch()} className="text-primary font-bold hover:underline">Réessayer</button>
        </div>
      ) : isLoading || !s ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{[0, 1, 2, 3].map((i) => <div key={i} className="h-32 skeleton rounded-2xl" />)}</div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <Tuile titre="Utilisateurs" valeur={s.utilisateurs.total.toLocaleString("fr-FR")} detail={`+${s.utilisateurs.nouveaux_30j} en 30 j · ${s.utilisateurs.hotes} hôtes`} icone={Users} href="/backoffice/utilisateurs" />
            <Tuile titre="Annonces" valeur={s.annonces.visibles.toLocaleString("fr-FR")} detail={`visibles sur ${s.annonces.total} · ${s.annonces.verifiees} vérifiées`} icone={Home} href="/backoffice/annonces" />
            <Tuile titre="Réservations (30 j)" valeur={s.reservations.confirmees_30j.toLocaleString("fr-FR")} detail={`${s.reservations.annulees_30j} annulée${s.reservations.annulees_30j > 1 ? "s" : ""}`} icone={CalendarCheck} href="/backoffice/reservations" />
            <Tuile
              titre="Volume réservé (30 j)" icone={CalendarCheck} href="/backoffice/reservations"
              valeur={`${s.reservations.volume_30j.toLocaleString("fr-FR", { notation: "compact", maximumFractionDigits: 2 })} FCFA`}
              detail={formatPrice(s.reservations.volume_30j)}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-5">
              <ReservationsChart jours={s.reservations_par_jour} />
            </div>
            <div className="space-y-4">
              <Tuile
                titre="Avis" valeur={s.avis.moyenne !== null ? `${s.avis.moyenne.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} / 5` : "-"}
                detail={`${s.avis.total} avis vérifiés`} icone={Star} href="/backoffice/avis"
              />
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <p className="text-sm font-semibold text-dark mb-3">À traiter</p>
                <ul className="space-y-2 text-sm">
                  <li>
                    <Link href="/agent"
                      className={pieces > 0
                        ? "flex items-center justify-between gap-2 -mx-2 px-2 py-2 rounded-xl bg-orange-50 text-orange-900 font-semibold hover:bg-orange-100"
                        : "flex items-center justify-between gap-2 hover:text-primary"}>
                      <span className="flex items-center gap-2"><IdCard size={15} className={pieces > 0 ? "text-orange-700" : "text-gray-400"} /> Pièces d&apos;identité à contrôler</span>
                      {pieces > 0 ? (
                        <span className="flex items-center gap-1">
                          <span className="min-w-[22px] h-[22px] px-1.5 rounded-full bg-orange-700 text-white text-xs font-bold tabular-nums flex items-center justify-center">{pieces}</span>
                          <ChevronRight size={16} className="text-orange-700" aria-hidden />
                        </span>
                      ) : <span className="font-bold tabular-nums">0</span>}
                    </Link>
                  </li>
                  <li>
                    <Link href="/backoffice/annonces?statut=en_attente" className="flex items-center justify-between hover:text-primary">
                      <span className="flex items-center gap-2"><BadgeCheck size={15} className="text-gray-400" /> Annonces à vérifier</span>
                      <span className="font-bold tabular-nums">{s.annonces.en_attente}</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/backoffice/utilisateurs?actif=false" className="flex items-center justify-between hover:text-primary">
                      <span className="flex items-center gap-2"><Users size={15} className="text-gray-400" /> Comptes désactivés</span>
                      <span className="font-bold tabular-nums">{s.utilisateurs.desactives}</span>
                    </Link>
                  </li>
                  <li>
                    <Link href="/backoffice/avis?note=1" className="flex items-center justify-between hover:text-primary">
                      <span className="flex items-center gap-2"><Star size={15} className="text-gray-400" /> Avis à 1 étoile</span>
                      <span className="text-xs text-muted" aria-hidden>voir</span>
                    </Link>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
