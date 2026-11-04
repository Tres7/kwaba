"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, FileText } from "lucide-react";
import { messageErreurPdf, telechargerPdf } from "@/lib/documents";
import { formatDate, formatPrice, isoDate } from "@/lib/utils";
import { lireFinances, URL_EXPORT_FINANCES } from "../api";

const PRODUITS: Record<string, string> = { reservation: "Séjours", transfert: "Transferts", location: "Locations", don: "Dons" };
const STATUTS: Record<string, string> = { planifie: "Planifié", en_cours: "En cours", envoye: "Envoyé", echoue: "Échoué", a_envoyer: "À envoyer", attente_numero: "Numéro attendu" };

function Chiffre({ libelle, montant, aide, accent }: { libelle: string; montant: number; aide?: string; accent?: boolean }) {
  return (
    <div className={`rounded-2xl p-4 ${accent ? "bg-primary text-white" : "bg-white border border-gray-100"}`}>
      <p className={`text-xs font-semibold ${accent ? "text-white/80" : "text-muted"}`}>{libelle}</p>
      <p className="font-heading font-bold text-xl mt-1 tabular-nums">{formatPrice(montant)}</p>
      {aide && <p className={`text-xs mt-0.5 ${accent ? "text-white/80" : "text-muted"}`}>{aide}</p>}
    </div>
  );
}

/**
 * Money of a period (AN-B2): collected, refunded, paid to the partners, due to them, Kwa-Ba's revenue, a day-by-day
 * reconciliation, and the exports (CSV: every movement; PDF: summary for the accounts).
 */
export default function Finances() {
  const aujourd_hui = new Date();
  const [debut, setDebut] = useState(isoDate(new Date(aujourd_hui.getFullYear(), aujourd_hui.getMonth(), 1)));
  const [fin, setFin] = useState(isoDate(aujourd_hui));
  const [export_, setExport] = useState<"" | "csv" | "pdf">("");
  const { data: d, isLoading, isError } = useQuery({
    queryKey: ["admin", "finances", debut, fin], queryFn: () => lireFinances(debut, fin), enabled: !!debut && !!fin && debut <= fin,
  });

  const exporter = async (format: "csv" | "pdf") => {
    setExport(format);
    try {
      await telechargerPdf(`${URL_EXPORT_FINANCES}${format}/?debut=${debut}&fin=${fin}`, `kwaba-finances.${format}`);
    } catch (err) {
      toast.error(await messageErreurPdf(err, "Export impossible."));
    } finally {
      setExport("");
    }
  };

  const champ = "px-3 py-2 border border-gray-200 rounded-xl text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const jours = d?.jours.filter((j) => j.nb_paiements || j.rembourse || j.verse) ?? [];
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end gap-3">
        <label className="text-sm"><span className="block text-xs font-semibold text-muted mb-1">Du</span>
          <input type="date" className={champ} value={debut} max={fin} onChange={(e) => setDebut(e.target.value)} /></label>
        <label className="text-sm"><span className="block text-xs font-semibold text-muted mb-1">Au</span>
          <input type="date" className={champ} value={fin} min={debut} onChange={(e) => setFin(e.target.value)} /></label>
        <div className="flex gap-2 sm:ml-auto">
          <button onClick={() => exporter("csv")} disabled={!!export_ || !d} className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-semibold disabled:opacity-50">
            <Download size={16} aria-hidden /> {export_ === "csv" ? "Export…" : "Export CSV"}
          </button>
          <button onClick={() => exporter("pdf")} disabled={!!export_ || !d} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-50">
            <FileText size={16} aria-hidden /> {export_ === "pdf" ? "Export…" : "Export PDF"}
          </button>
        </div>
      </div>

      {isLoading && <div className="h-64 skeleton rounded-2xl" />}
      {isError && <p className="text-sm text-red-700">Impossible de calculer cette période (un an au plus).</p>}
      {d && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Chiffre libelle="Encaissé" montant={d.totaux.encaisse} aide={`${d.totaux.nb_paiements} paiement${d.totaux.nb_paiements > 1 ? "s" : ""}`} />
            <Chiffre libelle="Remboursé" montant={d.totaux.rembourse} aide={d.totaux.rembourse_en_attente ? `${formatPrice(d.totaux.rembourse_en_attente)} en attente` : undefined} />
            <Chiffre libelle="Versé aux partenaires" montant={d.totaux.verse} />
            <Chiffre libelle="Dû aux partenaires" montant={d.totaux.du_partenaires} aide="Versements à venir ou en échec" />
            <Chiffre libelle="Revenu Kwa-Ba" montant={d.totaux.revenu_kwaba} aide="Frais de service et commissions" accent />
          </div>

          {Object.keys(d.par_produit).length > 0 && (
            <p className="text-sm text-muted">
              {Object.entries(d.par_produit).map(([p, m]) => `${PRODUITS[p] ?? p} : ${formatPrice(m)}`).join(" · ")}
            </p>
          )}

          <section className="bg-white rounded-2xl border border-gray-100 overflow-x-auto">
            <h2 className="font-heading font-bold text-dark px-5 pt-5">Rapprochement jour par jour</h2>
            <p className="text-xs text-muted px-5 mb-3">Solde du jour = encaissé − remboursé − versé.</p>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-muted border-b border-gray-100">
                <th className="px-5 py-2 font-semibold">Jour</th><th className="px-3 py-2 font-semibold text-right">Paiements</th>
                <th className="px-3 py-2 font-semibold text-right">Encaissé</th><th className="px-3 py-2 font-semibold text-right">Remboursé</th>
                <th className="px-3 py-2 font-semibold text-right">Versé</th><th className="px-5 py-2 font-semibold text-right">Solde</th>
              </tr></thead>
              <tbody className="tabular-nums">
                {jours.length === 0 && <tr><td colSpan={6} className="px-5 py-4 text-muted">Aucun mouvement sur la période.</td></tr>}
                {jours.map((j) => (
                  <tr key={j.date} className="border-b border-gray-50 last:border-0">
                    <td className="px-5 py-2">{formatDate(j.date)}</td><td className="px-3 py-2 text-right">{j.nb_paiements}</td>
                    <td className="px-3 py-2 text-right">{formatPrice(j.encaisse)}</td><td className="px-3 py-2 text-right">{formatPrice(j.rembourse)}</td>
                    <td className="px-3 py-2 text-right">{formatPrice(j.verse)}</td><td className="px-5 py-2 text-right font-semibold">{formatPrice(j.solde)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="bg-white rounded-2xl border border-gray-100 p-5">
            <h2 className="font-heading font-bold text-dark mb-3">Versements aux partenaires</h2>
            {d.versements.length === 0 ? <p className="text-sm text-muted">Aucun versement sur la période ni à venir.</p> : (
              <ul className="divide-y divide-gray-50 text-sm">
                {d.versements.map((v, i) => (
                  <li key={`${v.objet}-${i}`} className="flex flex-wrap justify-between gap-2 py-2">
                    <span className="min-w-0"><strong className="text-dark">{v.beneficiaire}</strong> <span className="text-muted">· {v.categorie} · {v.objet}</span></span>
                    <span className="tabular-nums whitespace-nowrap">{formatPrice(v.montant)} · {STATUTS[v.statut] ?? v.statut}
                      <span className="text-muted"> · {v.envoye_le ? `envoyé le ${formatDate(v.envoye_le)}` : `prévu le ${formatDate(v.date_prevue)}`}</span></span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
