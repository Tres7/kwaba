"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import api from "@/lib/api";
import PropertyCard from "@/components/hebergement/PropertyCard";
import type { Hebergement, Paginated } from "@/types/api/models";

const NOMBRE = 4;

/**
 * Bottom of a listing page: other stays in the same city, or the best rated ones when the city has too few,
 * so that a visitor who hesitates has somewhere to go next.
 */
export default function LogementsSimilaires({ hebergement }: { hebergement: Hebergement }) {
  const t = useTranslations("fiche");
  const { data } = useQuery({
    queryKey: ["hebergements", "similaires", hebergement.id],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const lire = async (params: Record<string, string | number>) =>
        (await api.get<Paginated<Hebergement>>("/v1/hebergements/", { params: { limit: NOMBRE + 1, ...params } })).data.results
          .filter((h) => h.id !== hebergement.id);
      const memeVille = await lire({ city: hebergement.city, sort: "note" });
      if (memeVille.length >= 2) return { ville: true, logements: memeVille.slice(0, NOMBRE) };
      const ailleurs = (await lire({ sort: "note" })).filter((h) => !memeVille.some((m) => m.id === h.id));
      return { ville: false, logements: [...memeVille, ...ailleurs].slice(0, NOMBRE) };
    },
  });

  if (!data || data.logements.length === 0) return null;
  return (
    <section aria-labelledby="similaires-titre" className="mt-14">
      <h2 id="similaires-titre" className="font-heading font-bold text-dark text-xl sm:text-2xl mb-5">
        {data.ville ? t("similairesVille", { ville: hebergement.city }) : t("similaires")}
      </h2>
      <div className="flex sm:grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 overflow-x-auto sm:overflow-visible snap-x snap-mandatory scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0 pb-2 sm:pb-0">
        {data.logements.map((h) => (
          <div key={h.id} className="w-[82%] flex-shrink-0 snap-start sm:w-auto">
            <PropertyCard property={h} />
          </div>
        ))}
      </div>
    </section>
  );
}
