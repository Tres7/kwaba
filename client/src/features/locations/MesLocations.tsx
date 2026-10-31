"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useFormat } from "@/lib/format";
import { listerMesLocations } from "./api";
import { clesLocations } from "./hooks";

export default function MesLocations() {
  const { formatDate } = useFormat();
  const t = useTranslations("location");
  const { status } = useSession();
  const { data } = useQuery({
    queryKey: clesLocations.mesLocations,
    queryFn: listerMesLocations,
    enabled: status === "authenticated",
  });
  if (!data?.length) return null;
  return (
    <section className="mt-12">
      <h2 className="font-heading font-bold text-dark text-xl mb-4">{t("mesLocations")}</h2>
      <ul className="space-y-3">
        {data.map((l) => (
          <li key={l.id}>
            <Link href={`/location/${l.id}`} className="flex items-center justify-between gap-3 bg-white rounded-2xl border border-gray-100 p-4 hover:border-primary/30">
              <span className="min-w-0">
                <span className="block font-semibold text-dark truncate">{l.libelle} · {l.lieu_prise_detail.ville}</span>
                <span className="block text-sm text-gray-500">{formatDate(l.debut_locale)} → {formatDate(l.fin_locale)} · <span className="font-mono text-xs">{l.reference}</span></span>
              </span>
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-gray-100 text-dark whitespace-nowrap">{t(`statuts.${l.statut}`)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Car and driver hire: partner owners' vehicles, filters, detailed request, online payment. */
