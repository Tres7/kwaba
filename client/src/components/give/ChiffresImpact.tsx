import type { Impact } from "@/types/api/give";
import { useLocale, useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

/** Collected / transferred / pending: transparency in three figures. */
export default function ChiffresImpact({ impact, clair = false }: { impact: Impact; clair?: boolean }) {
  const { formatPrice } = useFormat();
  const t = useTranslations("give");
  const locale = useLocale();
  const cases = [
    { label: t("collectesOng"), valeur: formatPrice(impact.collecte) },
    { label: t("dejaReverses"), valeur: formatPrice(impact.reverse) },
    { label: t("aReverser"), valeur: formatPrice(impact.en_attente) },
    { label: t("dons"), valeur: impact.nb_dons.toLocaleString(locale === "en" ? "en-GB" : "fr-FR") },
  ];
  return (
    <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {cases.map((c) => (
        <div key={c.label} className={clair ? "bg-white/10 rounded-2xl p-4" : "bg-white rounded-2xl border border-gray-100 p-4"}>
          <dt className={clair ? "text-xs text-white/80" : "text-xs text-gray-600"}>{c.label}</dt>
          <dd className={clair ? "font-heading font-bold text-lg text-white mt-1" : "font-heading font-bold text-lg text-dark mt-1"}>{c.valeur}</dd>
        </div>
      ))}
    </dl>
  );
}
