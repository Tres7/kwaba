import { Link } from "@/i18n/navigation";
import { BadgeCheck, MapPin } from "lucide-react";
import { useTextesGive } from "@/lib/give";
import { cn } from "@/lib/utils";
import type { Organisation } from "@/types/api/give";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

export default function CarteOrganisation({ o }: { o: Organisation }) {
  const { CAUSES, PAYS } = useTextesGive();
  const { formatPrice } = useFormat();
  const t = useTranslations("give");
  const cause = CAUSES[o.cause];
  return (
    <Link href={`/give/${o.slug}`} className="group flex flex-col bg-white rounded-3xl border border-gray-100 overflow-hidden hover:shadow-card transition-shadow">
      <div className="relative h-36 bg-primary/10">
        {o.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={o.image} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-primary/40"><cause.icon size={48} /></div>
        )}
        <span className={cn("absolute top-3 left-3 flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full", cause.couleur)}>
          <cause.icon size={12} /> {cause.nom}
        </span>
      </div>
      <div className="flex-1 flex flex-col p-5">
        <div className="flex items-center gap-3">
          {o.logo && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={o.logo} alt="" className="w-10 h-10 rounded-xl object-cover border border-gray-100 flex-shrink-0" />
          )}
          <div className="min-w-0">
            <p className="font-heading font-bold text-dark leading-tight group-hover:text-primary">{o.nom}</p>
            <p className="flex items-center gap-1 text-xs text-gray-600 mt-0.5">
              <MapPin size={12} /> {o.ville}, {PAYS[o.pays] ?? o.pays}
            </p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-3 flex-1">{o.resume}</p>
        <div className="flex items-center justify-between gap-2 mt-4 pt-4 border-t border-gray-100 text-xs">
          <span className="flex items-center gap-1 font-semibold text-primary"><BadgeCheck size={14} /> {t("verifiee")}</span>
          <span className="text-gray-600">{o.impact.nb_dons > 0 ? t("collectes", { montant: formatPrice(o.impact.collecte) }) : t("premier")}</span>
        </div>
      </div>
    </Link>
  );
}
