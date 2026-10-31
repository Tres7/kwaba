"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { useState } from "react";
import { Car, MapPin, Star, Users } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { FALLBACK_IMAGE } from "@/lib/utils";
import { useLocale, useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { creerVoyageDeGroupe } from "./api";
import type { Carte, CarteLogement, CarteTogether, CarteTransfert } from "./types";

function Logement({ c }: { c: CarteLogement }) {
  const { formatPrice } = useFormat();
  const t = useTranslations("conciergeCartes");
  const sejour = c.arrivee && c.depart ? `?check_in=${c.arrivee}&check_out=${c.depart}&guests=${c.voyageurs ?? 1}` : "";
  return (
    <article className="w-60 flex-shrink-0 bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
      <img src={c.image || FALLBACK_IMAGE} alt={c.nom} className="w-full h-32 object-cover" />
      <div className="p-3">
        <p className="font-bold text-sm text-dark truncate">{c.nom}</p>
        <p className="flex items-center gap-1 text-xs text-gray-600 truncate"><MapPin size={11} className="text-primary flex-shrink-0" /> {c.quartier || c.ville}</p>
        <p className="flex items-center gap-2 text-xs text-gray-600 mt-1">
          {c.nb_avis > 0 && <span className="flex items-center gap-0.5"><Star size={11} className="fill-accent text-accent" /> {c.note.toFixed(1)}</span>}
          <span className="flex items-center gap-0.5"><Users size={11} /> {c.capacite}</span>
        </p>
        <p className="text-sm text-dark mt-2"><strong>{formatPrice(c.prix_nuit)}</strong> <span className="text-xs text-gray-600">/ nuit</span></p>
        {c.total !== null && <p className="text-xs text-gray-600">{formatPrice(c.total)} pour {c.nuits} nuit{(c.nuits ?? 0) > 1 ? "s" : ""}, frais compris</p>}
        <div className="flex gap-2 mt-3">
          <Link href={`/hebergements/${c.id}${sejour}`} className="flex-1 text-center px-3 py-2 rounded-xl border border-gray-200 text-xs font-bold text-dark hover:bg-gray-50">{t("voir")}</Link>
          {sejour && <Link href={`/reservation/${c.id}${sejour}`} className="flex-1 text-center px-3 py-2 rounded-xl bg-secondary text-white text-xs font-bold">{t("reserver")}</Link>}
        </div>
      </div>
    </article>
  );
}

function Transfert({ c }: { c: CarteTransfert }) {
  const { formatDate, formatPrice } = useFormat();
  const t = useTranslations("conciergeCartes");
  const locale = useLocale();
  const tT = useTranslations("transfert");
  const [jour, heure] = c.arrivee.split("T");
  const lien = `/transfert?aeroport=${c.aeroport}&date=${jour}&heure=${heure}&passagers=${c.passagers}&bagages=${c.bagages}`;
  return (
    <article className="w-72 flex-shrink-0 bg-dark text-white rounded-2xl p-4">
      <p className="flex items-center gap-2 font-bold text-sm"><Car size={16} /> {t("transfertDepuis", { ville: c.ville })}</p>
      <p className="text-xs text-white/75 mt-1">{t("detailVol", { date: formatDate(jour), heure: locale === "en" ? heure : heure.replace(":", " h "), passagers: c.passagers, bagages: c.bagages })}</p>
      <ul className="mt-3 space-y-1.5 text-sm">
        {c.options.filter((o) => o.disponible).map((o) => (
          <li key={o.categorie} className="flex justify-between gap-3"><span>{tT(`vehicules.${o.categorie}.nom`)}</span><strong>{formatPrice(o.prix)}</strong></li>
        ))}
      </ul>
      {c.trop_tard ? (
        <p className="text-xs text-orange-200 mt-3">{t("tropTard")}</p>
      ) : (
        <Link href={lien} className="mt-3 flex items-center justify-center gap-1.5 w-full py-2 rounded-xl bg-white text-dark text-xs font-bold">
          {t("reserverTransfert")}
        </Link>
      )}
    </article>
  );
}

function Together({ c }: { c: CarteTogether }) {
  const { formatDate } = useFormat();
  const t = useTranslations("conciergeCartes");
  const tV = useTranslations("voyageurs");
  const router = useRouter();
  const [envoi, setEnvoi] = useState(false);
  const creer = async () => {
    setEnvoi(true);
    try {
      router.push(`/together/${await creerVoyageDeGroupe(c)}?nouveau=1`);
    } catch (err) {
      toast.error(apiErrorMessage(err, t("erreurVoyage")));
      setEnvoi(false);
    }
  };
  return (
    <article className="w-72 flex-shrink-0 bg-primary/5 border border-primary/20 rounded-2xl p-4">
      <p className="flex items-center gap-2 font-bold text-sm text-dark"><Users size={16} className="text-primary" /> {t("voyageGroupe", { nom: c.nom })}</p>
      <p className="text-xs text-gray-600 mt-1">
        {c.destination} · {tV("voyageurs", { nombre: c.voyageurs })}
        {c.arrivee && c.depart && <> · {formatDate(c.arrivee)} → {formatDate(c.depart)}</>}
      </p>
      {c.logements.length > 0 && <p className="text-xs text-dark mt-2">{t("aVoter", { liste: c.logements.map((l) => l.nom).join(", ") })}</p>}
      <button onClick={creer} disabled={envoi} className="mt-3 w-full py-2 rounded-xl bg-primary text-white text-xs font-bold disabled:opacity-60">
        {envoi ? t("creation") : t("creerVoyage")}
      </button>
    </article>
  );
}

export default function CartesConcierge({ cartes }: { cartes: Carte[] }) {
  const t = useTranslations("conciergeCartes");
  if (!cartes.length) return null;
  return (
    <div className="flex gap-3 overflow-x-auto scrollbar-hide pb-1 -mx-1 px-1" aria-label={t("offres")}>
      {cartes.map((c, i) =>
        c.type === "logement" ? <Logement key={`${c.id}-${i}`} c={c} />
          : c.type === "transfert" ? <Transfert key={`t-${i}`} c={c} />
            : <Together key={`g-${i}`} c={c} />,
      )}
    </div>
  );
}
