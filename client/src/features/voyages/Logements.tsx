"use client";

import RatingBadge from "@/components/ui/RatingBadge";
import { Link } from "@/i18n/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, Plus, Search, Trash2, Vote } from "lucide-react";
import { toast } from "sonner";
import { cn, FALLBACK_IMAGE } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { chercherLogements, proposerLogement, retenirProposition, retirerProposition, retirerVote, voter } from "./api";
import { messageErreur } from "./erreurs";
import type { SectionVoyage, Voyage } from "./types";

export default function Logements({ v, appliquer, recharger }: SectionVoyage) {
  const { formatPrice } = useFormat();
  const t = useTranslations("voyage");
  const [recherche, setRecherche] = useState(v.destination);
  const [ouvert, setOuvert] = useState(v.propositions.length === 0);
  const deja = new Set(v.propositions.map((p) => p.hebergement.id));

  const { data: resultats = [], isFetching } = useQuery({
    queryKey: ["hebergements", "together", recherche, v.date_debut, v.date_fin],
    queryFn: () => chercherLogements({ q: recherche || undefined, check_in: v.date_debut || undefined, check_out: v.date_fin || undefined, limit: 12 }),
    enabled: ouvert,
  });

  const action = async (fn: () => Promise<Voyage>, succes?: string) => {
    try {
      const voyage = await fn();
      if (voyage?.id) appliquer(voyage);
      else recharger();
      if (succes) toast.success(succes);
    } catch (err) {
      toast.error(messageErreur(err, t("actionEchouee")));
    }
  };

  const retenue = v.propositions.find((p) => p.id === v.proposition_retenue);
  const reserverUrl = retenue && v.date_debut && v.date_fin
    ? `/reservation/${retenue.hebergement.id}?check_in=${v.date_debut}&check_out=${v.date_fin}&guests=${Math.min(v.nb_voyageurs, retenue.hebergement.max_guests)}`
    : null;

  return (
    <div className="space-y-5">
      {retenue && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 bg-secondary/10 border border-secondary/30 rounded-2xl p-4">
          <Award size={22} className="text-secondary flex-shrink-0" />
          <p className="flex-1 text-sm text-dark">{t.rich("retenu", { nom: retenue.hebergement.name, strong: (x) => <strong>{x}</strong> })}
            {retenue.budget && <>, {t("parPersonne", { montant: formatPrice(retenue.budget.par_personne) })}</>}</p>
          {reserverUrl && v.est_organisateur && (
            <Link href={reserverUrl} className="px-5 py-2.5 rounded-full bg-secondary text-white text-sm font-bold text-center">{t("reserverGroupe")}</Link>
          )}
        </div>
      )}

      {!v.nuits && (
        <p className="text-sm text-amber-900 bg-amber-50 rounded-xl px-4 py-3">
          {t("ajoutezDates")}
        </p>
      )}

      {v.propositions.length === 0 ? (
        <p className="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-600">{t("aucunePropo")}</p>
      ) : (
        <ul className="space-y-3">
          {v.propositions.map((p) => {
            const h = p.hebergement;
            const monChoix = v.mon_vote === p.id;
            return (
              <li key={p.id} className={cn("bg-white rounded-2xl border p-4 flex flex-col sm:flex-row gap-4", monChoix ? "border-primary" : "border-gray-100")}>
                <Link href={`/hebergements/${h.id}`} className="sm:w-40 h-32 flex-shrink-0">
                  <img src={h.image_url || FALLBACK_IMAGE} alt={h.name} className="w-full h-full object-cover rounded-xl" />
                </Link>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link href={`/hebergements/${h.id}`} className="font-heading font-bold text-dark hover:text-primary">{h.name}</Link>
                      <p className="text-sm text-gray-600">{h.city} · {t("persMax", { nombre: h.max_guests })} · {t("prixNuit", { prix: formatPrice(h.price_per_night) })}</p>
                      <RatingBadge rating={h.rating} count={h.review_count} className="mt-1" />
                    </div>
                    {v.proposition_retenue === p.id && <span className="text-xs font-bold bg-secondary text-white px-2.5 py-1 rounded-full">{t("retenuBadge")}</span>}
                  </div>
                  {p.commentaire && <p className="text-sm text-gray-700 italic mt-2">« {p.commentaire} » · {p.propose_par}</p>}
                  <div className="flex flex-wrap gap-2 mt-2 text-xs">
                    {p.disponible === false && <span className="px-2 py-1 rounded-full bg-red-50 text-red-700 font-semibold">{t("pris")}</span>}
                    {!p.assez_grand && <span className="px-2 py-1 rounded-full bg-amber-50 text-amber-800 font-semibold">{t("tropPetit", { nombre: v.nb_voyageurs })}</span>}
                  </div>
                </div>
                <div className="sm:w-48 flex sm:flex-col items-center sm:items-end justify-between gap-2">
                  {p.budget ? (
                    <div className="sm:text-right">
                      <p className="font-heading font-bold text-dark text-lg">{formatPrice(p.budget.par_personne)}</p>
                      <p className="text-xs text-gray-600">{t("parPersonneTotal", { total: formatPrice(p.budget.total) })}</p>
                    </div>
                  ) : <span />}
                  <div className="flex flex-wrap justify-end gap-2">
                    <button
                      onClick={() => action(() => (monChoix ? retirerVote(v.id) : voter(v.id, p.id)))}
                      aria-pressed={monChoix}
                      className={cn("flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold",
                        monChoix ? "bg-primary text-white" : "border border-primary/40 text-primary hover:bg-primary/5")}
                    >
                      <Vote size={15} /> {t("votes", { nombre: p.votes })}{monChoix && <span className="sr-only"> ({t("votreChoix")})</span>}
                    </button>
                    {v.est_organisateur && v.proposition_retenue !== p.id && (
                      <button onClick={() => action(() => retenirProposition(v.id, p.id), t("retenuToast"))}
                        className="px-3 py-2 rounded-full border border-gray-200 text-xs font-bold text-dark hover:bg-gray-50">{t("retenir")}</button>
                    )}
                    {p.peut_supprimer && (
                      <button onClick={() => action(() => retirerProposition(v.id, p.id))}
                        aria-label={t("retirerPropo", { nom: h.name })} className="p-2 rounded-full text-gray-500 hover:text-red-700 hover:bg-red-50">
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                  {p.votants.length > 0 && <p className="text-[11px] text-gray-600 sm:text-right">{p.votants.join(", ")}</p>}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <section className="bg-white rounded-2xl border border-gray-100 p-5">
        <button onClick={() => setOuvert(!ouvert)} aria-expanded={ouvert} className="flex items-center gap-2 font-heading font-bold text-dark">
          <Plus size={18} className="text-primary" /> {t("proposerLogement")}
        </button>
        {ouvert && (
          <div className="mt-4">
            <div className="relative">
              <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input value={recherche} onChange={(e) => setRecherche(e.target.value)} aria-label={t("rechercherLogement")}
                placeholder={t("rechercherPlaceholder")} className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-base sm:text-sm outline-none focus:border-primary/50" />
            </div>
            <ul className={cn("grid sm:grid-cols-2 gap-3 mt-3", isFetching && "opacity-60")}>
              {resultats.filter((h) => !deja.has(h.id)).map((h) => (
                <li key={h.id} className="flex items-center gap-3 p-2 rounded-xl border border-gray-100">
                  <img src={h.image_url || FALLBACK_IMAGE} alt="" className="w-16 h-14 rounded-lg object-cover flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-sm text-dark truncate">{h.name}</p>
                    <p className="text-xs text-gray-600">{h.city} · {t("prixNuit", { prix: formatPrice(h.price_per_night) })}</p>
                  </div>
                  <button onClick={() => action(() => proposerLogement(v.id, h.id), t("proposeToast"))}
                    className="px-3 py-1.5 rounded-full bg-primary text-white text-xs font-bold">{t("proposer")}</button>
                </li>
              ))}
              {!isFetching && resultats.length === 0 && <li className="text-sm text-gray-600">{v.date_debut ? t("aucunDispoDates") : t("aucunDispo")}</li>}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
