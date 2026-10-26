import { CheckCircle, Clock, FileText } from "lucide-react";
import { moisAnnee } from "@/lib/give";
import { formatDate, formatPrice } from "@/lib/utils";
import type { Reversement } from "@/types/api/give";
import { useTranslations } from "next-intl";

/** One transfer line: amount, date and proof of the transfer (public). */
export default function PreuveReversement({ r, avecOrganisation = false }: { r: Reversement; avecOrganisation?: boolean }) {
  const t = useTranslations("give");
  const fait = r.statut === "effectue";
  return (
    <li className="flex flex-wrap items-center gap-3 bg-white rounded-2xl border border-gray-100 p-4">
      <span className={fait ? "text-secondary" : "text-amber-600"}>{fait ? <CheckCircle size={20} /> : <Clock size={20} />}</span>
      <div className="flex-1 min-w-[12rem]">
        <p className="font-bold text-dark text-sm">
          {avecOrganisation && <>{r.organisation.nom} · </>}{t("donsDe", { mois: moisAnnee(r.periode) })}
        </p>
        <p className="text-xs text-gray-600 mt-0.5">
          {formatPrice(r.montant)} · {t("nbDons", { nombre: r.nb_dons })} ·{" "}
          {fait ? t("reversesLe", { date: formatDate(r.effectue_le ?? "") }) : t("prevuLe", { date: formatDate(r.date_prevue) })}
          {fait && r.reference_operation && <> · {t("ref", { reference: r.reference_operation })}</>}
        </p>
        {r.note && <p className="text-xs text-dark mt-1.5 italic">« {r.note} »</p>}
      </div>
      {r.justificatif && (
        <a href={r.justificatif} target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs font-bold text-primary border border-primary/30 rounded-full px-3 py-1.5 hover:bg-primary/5">
          <FileText size={14} /> {t("preuve")}<span className="sr-only"> ({t("nouvelOnglet")})</span>
        </a>
      )}
    </li>
  );
}
