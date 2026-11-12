"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { TriangleAlert } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { formatDate, TYPE_LABELS } from "@/lib/utils";
import { lireTarifsAdmin, modifierTarifsAdmin, type TarifsAdmin } from "../api";

const TAUX: { cle: keyof TarifsAdmin["taux"]; libelle: string; aide: string }[] = [
  { cle: "frais_voyageur", libelle: "Frais de service voyageur", aide: "Sur le prix des nuits, payés par le voyageur." },
  { cle: "frais_reduits", libelle: "Frais réduits", aide: "Client fidèle et Pack Séjour + Chauffeur." },
  { cle: "commission_particulier", libelle: "Commission hôte particulier", aide: "Retenue sur le prix des nuits." },
  { cle: "commission_hotel", libelle: "Commission hôtel ou résidence", aide: "Comptes classés « hôtel » (Utilisateurs → Commission)." },
  { cle: "commission_fondateur", libelle: "Commission Programme Fondateurs", aide: "Pendant les dates du programme de l'hôte." },
  { cle: "commission_transfert", libelle: "Commission transferts aéroport", aide: "Part du prix gardée par Kwa-Ba, le reste va au chauffeur." },
];

/**
 * Kwa-Ba's rates and the cleaning fee scale, changed without a deployment (AN-B1). The site, the terms of sale and the
 * contracts read them: a change shows everywhere at once, for the bookings made afterwards.
 */
export default function Tarifs() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin", "tarifs"], queryFn: lireTarifsAdmin });
  const [taux, setTaux] = useState<Record<string, string>>({});
  const [menage, setMenage] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!data) return;
    setTaux(Object.fromEntries(Object.entries(data.taux).map(([k, v]) => [k, String(v)])));
    setMenage(Object.fromEntries(Object.entries(data.frais_menage).map(([k, v]) => [k, String(v)])));
  }, [data]);

  const enregistrer = async () => {
    setEnvoi(true);
    try {
      await modifierTarifsAdmin({
        taux: Object.fromEntries(Object.entries(taux).map(([k, v]) => [k, Number(v.replace(",", "."))])) as TarifsAdmin["taux"],
        frais_menage: Object.fromEntries(Object.entries(menage).map(([k, v]) => [k, Math.round(Number(v))])),
      });
      toast.success("Tarifs enregistrés : ils s'appliquent aux prochaines réservations.");
      queryClient.invalidateQueries({ queryKey: ["admin", "tarifs"] });
      queryClient.invalidateQueries({ queryKey: ["paiements", "config"] });
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setEnvoi(false);
    }
  };

  if (isLoading || !data) return <div className="h-96 skeleton rounded-2xl" />;
  const champ = "w-28 px-3 py-2 border border-gray-200 rounded-xl text-right tabular-nums text-base sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary";
  return (
    <div className="space-y-6">
      <p className="flex items-start gap-2 rounded-2xl bg-amber-50 text-amber-900 px-4 py-3 text-sm">
        <TriangleAlert size={18} className="shrink-0 mt-0.5" aria-hidden />
        <span>
          Un changement s&apos;applique aux réservations faites ensuite ; les réservations déjà faites gardent leurs montants.
          Le site, les CGV et les contrats affichent aussitôt les nouveaux taux. Les CGV (art. 23.1) prévoient d&apos;annoncer une
          modification importante aux clients 30 jours à l&apos;avance.
        </span>
      </p>
      <section className="bg-white rounded-2xl border border-gray-100 p-5">
        <h2 className="font-heading font-bold text-dark mb-4">Taux</h2>
        <div className="divide-y divide-gray-100">
          {TAUX.map(({ cle, libelle, aide }) => (
            <label key={cle} className="flex items-center justify-between gap-4 py-3">
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-dark">{libelle}</span>
                <span className="block text-xs text-muted">{aide}</span>
              </span>
              <span className="flex items-center gap-2 shrink-0">
                <input inputMode="decimal" className={champ} value={taux[cle] ?? ""} onChange={(e) => setTaux((t) => ({ ...t, [cle]: e.target.value }))} />
                <span className="text-sm text-muted">%</span>
              </span>
            </label>
          ))}
        </div>
      </section>
      <section className="bg-white rounded-2xl border border-gray-100 p-5">
        <h2 className="font-heading font-bold text-dark mb-1">Frais de ménage</h2>
        <p className="text-xs text-muted mb-3">Par séjour et par logement, reversés en totalité à l&apos;hôte.</p>
        <div className="divide-y divide-gray-100">
          {Object.keys(menage).map((code) => (
            <label key={code} className="flex items-center justify-between gap-4 py-2.5">
              <span className="text-sm font-medium text-dark">{TYPE_LABELS[code]}</span>
              <span className="flex items-center gap-2">
                <input inputMode="numeric" className={champ} value={menage[code]} onChange={(e) => setMenage((m) => ({ ...m, [code]: e.target.value }))} />
                <span className="text-sm text-muted">F CFA</span>
              </span>
            </label>
          ))}
        </div>
      </section>
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-muted">{data.mis_a_jour_le ? `Modifiés le ${formatDate(data.mis_a_jour_le)}` : "Grille d'origine (18 octobre 2026)"}</p>
        <button onClick={enregistrer} disabled={envoi} className="px-6 py-3 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary-600 disabled:opacity-50">
          {envoi ? "Enregistrement…" : "Enregistrer les tarifs"}
        </button>
      </div>
    </div>
  );
}
