import { useTranslations } from "next-intl";
import { ShieldCheck } from "lucide-react";
import { Link } from "@/i18n/navigation";
import type { PolitiqueAnnulation as Politique } from "@/types/api/models";

/** Cancellation policy chosen by the host (terms of sale, appendix 1), with the 48-hour cooling-off period. */
export default function PolitiqueAnnulation({ politique, compact = false }: { politique: Politique; compact?: boolean }) {
  const t = useTranslations("politiqueAnnulation");
  const contenu = (
    <>
      <p className="text-sm text-dark"><strong>{t(`${politique}.nom`)}</strong> : {t(`${politique}.regle`)}</p>
      <p className="text-xs text-gray-600 mt-1.5 leading-relaxed">{t("reflexion")}</p>
      <Link href="/remboursement" className="inline-block text-xs text-primary font-semibold hover:underline mt-1.5">{t("details")}</Link>
    </>
  );
  if (compact) {
    return (
      <div className="flex items-start gap-2 bg-gray-50 rounded-xl p-3">
        <ShieldCheck size={16} className="text-secondary flex-shrink-0 mt-0.5" aria-hidden />
        <div>{contenu}</div>
      </div>
    );
  }
  return (
    <section className="bg-white rounded-2xl shadow-card p-5 sm:p-6">
      <h2 className="font-heading font-bold text-dark text-xl mb-3">{t("titre")}</h2>
      {contenu}
    </section>
  );
}
