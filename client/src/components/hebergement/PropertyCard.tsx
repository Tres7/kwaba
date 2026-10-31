import { Link } from "@/i18n/navigation";
import { BadgeCheck, CalendarX, Flame, MapPin } from "lucide-react";
import type { Hebergement } from "@/types/api/models";
import { FavoriteButton } from "@/features/favoris";
import RatingBadge from "@/components/ui/RatingBadge";
import { FALLBACK_IMAGE, SERVICE_FEE_RATE, cn, prixNuitFraisInclus } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { useResumeDetails } from "@/components/hebergement/DetailsLogement";
import { useFormat } from "@/lib/format";

/** "Only N left" from this number of units (hotels and other multi-unit establishments). */
const SEUIL_STOCK_FAIBLE = 3;

interface PropertyCardProps {
  property: Hebergement;
  query?: string;
  onFavoriteChange?: (isFavorite: boolean) => void;
}

export default function PropertyCard({ property, query = "", onFavoriteChange }: PropertyCardProps) {
  const { TYPE_LABELS, formatDate, formatPrice } = useFormat();
  const resume = useResumeDetails();
  const t = useTranslations("logement");
  const prix = Number(property.price_per_night);
  const { frais, total } = prixNuitFraisInclus(prix, property.frais_voyageur ?? SERVICE_FEE_RATE);
  // Search with dates: a full listing stays visible (photos, description) with its next free date
  const dispo = property.disponibilite;
  const complet = dispo?.disponible === false;
  const peuDeChoix = dispo?.disponible && dispo.unites_total > 1 && dispo.unites_restantes <= SEUIL_STOCK_FAIBLE;
  return (
    <Link
      href={`/hebergements/${property.id}${query}`}
      className="group bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-shadow overflow-hidden flex flex-col h-full"
    >
      <div className="relative aspect-[4/3] bg-slate-100 overflow-hidden">
        <img
          src={property.image_url || FALLBACK_IMAGE}
          alt={property.name}
          loading="lazy"
          className={cn("w-full h-full object-cover transition-transform duration-500 group-hover:scale-105", complet && "opacity-75")}
        />
        {complet && (
          <span className="absolute bottom-3 left-3 flex items-center gap-1.5 bg-dark/85 text-white px-2.5 py-1 text-xs font-bold rounded-full">
            <CalendarX size={13} aria-hidden /> {t("completDates")}
          </span>
        )}
        {peuDeChoix && (
          <span className="absolute bottom-3 left-3 flex items-center gap-1.5 bg-amber-500 text-dark px-2.5 py-1 text-xs font-bold rounded-full">
            <Flame size={13} aria-hidden /> {t("plusQue", { nombre: dispo!.unites_restantes })}
          </span>
        )}
        <span className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full text-dark shadow-sm">
          {TYPE_LABELS[property.type] ?? property.type}
        </span>
        <FavoriteButton
          hebergementId={property.id}
          initial={property.is_favorite}
          onChange={onFavoriteChange}
          className="absolute top-3 right-3"
        />
      </div>

      <div className="p-4 flex flex-col flex-1">
        <div className="flex justify-between items-start gap-2">
          <h3 className="font-heading font-semibold text-dark text-[15px] leading-snug flex items-center gap-1 min-w-0">
            <span className="truncate">{property.name}</span>
            {property.est_verifie && <BadgeCheck size={15} className="text-secondary flex-shrink-0" aria-label={t("verifie")} />}
          </h3>
          <RatingBadge rating={property.rating} count={property.review_count} className="flex-shrink-0" />
        </div>
        <div className="flex items-center gap-1 mt-1 text-gray-500">
          <MapPin size={11} className="flex-shrink-0" />
          <span className="text-xs truncate">{property.location ? `${property.location}, ` : ""}{property.city}</span>
        </div>
        {resume(property) && <p className="text-xs text-gray-600 mt-1 truncate">{resume(property)}</p>}
        {complet && (
          <p className="text-xs font-semibold text-dark mt-1.5">
            {dispo!.prochaine_date
              ? t("disponibleDes", { date: formatDate(dispo!.prochaine_date, { day: "numeric", month: "long" }) })
              : t("aucuneDateProche")}
          </p>
        )}
        <p className="mt-auto pt-3 text-sm" title={t("detailPrix", { prix: formatPrice(prix), frais: formatPrice(frais) })}>
          <span className="font-heading font-bold text-primary">{formatPrice(total)}</span>
          <span className="text-gray-500 text-xs"> {t("parNuitFraisInclus")}</span>
        </p>
      </div>
    </Link>
  );
}
