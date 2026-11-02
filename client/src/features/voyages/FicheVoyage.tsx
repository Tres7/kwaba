"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Check, Home, MapPin, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { lireVoyage } from "./api";
import { clesVoyages } from "./hooks";
import Itineraire from "./Itineraire";
import Logements from "./Logements";
import Membres from "./Membres";
import Reservations from "./Reservations";
import type { Voyage } from "./types";

type Onglet = "logements" | "itineraire" | "reservations" | "membres";

const ONGLETS: { id: Onglet; label: string; icon: typeof Home }[] = [
  { id: "logements", label: "logements", icon: Home },
  { id: "itineraire", label: "itineraire", icon: CalendarDays },
  { id: "reservations", label: "reservations", icon: Check },
  { id: "membres", label: "membres", icon: Users },
];

function VoyageContent() {
  const { formatDate } = useFormat();
  const t = useTranslations("voyage");
  const tT = useTranslations("together");
  const tFiche = useTranslations("fiche");
  const tVoy = useTranslations("voyageurs");
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [onglet, setOnglet] = useState<Onglet>("logements");
  const cle = clesVoyages.voyage(params.id);

  const { data: v, isError } = useQuery({
    queryKey: cle,
    queryFn: () => lireVoyage(params.id),
    // The other members vote and suggest: refresh regularly
    refetchInterval: 15000,
    retry: false,
  });

  useEffect(() => {
    if (searchParams.get("nouveau") === "1") {
      setOnglet("membres");
      router.replace(`/together/${params.id}`);
    }
  }, [searchParams, router, params.id]);

  const appliquer = (data: Voyage) => queryClient.setQueryData(cle, data);
  const recharger = () => queryClient.invalidateQueries({ queryKey: cle });

  if (isError) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-3 text-center px-6">
        <p className="font-heading font-bold text-xl text-dark">{t("introuvable")}</p>
        <p className="text-gray-600 text-sm">{t("introuvableTexte")}</p>
        <Link href="/together" className="text-primary font-bold hover:underline">{t("mesVoyagesGroupe")}</Link>
      </div>
    );
  }
  if (!v) return <div className="max-w-5xl mx-auto px-4 py-10"><div className="h-96 skeleton rounded-3xl" /></div>;

  return (
    <div className="bg-light min-h-[70vh] pb-12">
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-0">
          <Link href="/together" className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-dark"><ArrowLeft size={16} /> {t("mesVoyages")}</Link>
          <div className="flex flex-wrap items-end justify-between gap-3 mt-3">
            <div>
              <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl">{v.nom}</h1>
              <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600 mt-1">
                <span className="flex items-center gap-1"><MapPin size={14} className="text-primary" /> {v.destination}</span>
                {v.date_debut && v.date_fin
                  ? <span>{formatDate(v.date_debut)} → {formatDate(v.date_fin)} · {tFiche("nuits", { nombre: v.nuits ?? 0 })}</span>
                  : <span>{t("datesADefinir")}</span>}
                <span>{tVoy("voyageurs", { nombre: v.nb_voyageurs })}</span>
              </p>
            </div>
            <div className="flex -space-x-2" aria-label={tT("membres", { nombre: v.membres.length })}>
              {v.membres.slice(0, 6).map((m) => (
                <span key={m.id} title={m.nom} className="w-9 h-9 rounded-full bg-primary/10 border-2 border-white text-primary text-xs font-bold flex items-center justify-center">
                  {m.nom.split(" ").map((x) => x[0]).join("").slice(0, 2).toUpperCase()}
                </span>
              ))}
            </div>
          </div>
          <div className="flex gap-6 mt-5 overflow-x-auto scrollbar-hide" role="tablist">
            {ONGLETS.map(({ id, label, icon: Icon }) => (
              <button key={id} role="tab" aria-selected={onglet === id} onClick={() => setOnglet(id)}
                className={cn("flex items-center gap-1.5 pb-3 text-sm font-bold whitespace-nowrap border-b-2 transition-colors",
                  onglet === id ? "text-primary border-primary" : "text-gray-500 border-transparent hover:text-dark")}>
                <Icon size={15} /> {t(`onglets.${label}`)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
        {onglet === "logements" && <Logements v={v} appliquer={appliquer} recharger={recharger} />}
        {onglet === "itineraire" && <Itineraire v={v} appliquer={appliquer} recharger={recharger} />}
        {onglet === "reservations" && <Reservations v={v} appliquer={appliquer} recharger={recharger} />}
        {onglet === "membres" && <Membres v={v} recharger={recharger} />}
      </div>
    </div>
  );
}

export default function VoyagePage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] bg-light" />}>
      <VoyageContent />
    </Suspense>
  );
}
