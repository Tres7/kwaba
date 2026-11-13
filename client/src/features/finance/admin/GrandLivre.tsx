"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, TriangleAlert } from "lucide-react";
import { formatDate, formatPrice } from "@/lib/utils";
import { lireGrandLivre, type MouvementFinance } from "../api";

const TIERS: Record<string, string> = {
  hote: "Hôte", hotel: "Hôtel", voyageur: "Voyageur", chauffeur: "Chauffeur", proprietaire: "Propriétaire",
  prestataire: "Prestataire", apporteur: "Apporteur",
};
const OFFRES: Record<string, string> = {
  COURTE_DUREE: "Courte durée", HOTEL: "Hôtel", TRANSFERT: "Transfert", VOITURE_CH: "Voiture avec chauffeur",
  VOITURE_SANS: "Voiture sans chauffeur", STRUCTURE: "Structure", EVASION: "Évasion",
};
const FAMILLES: Record<string, string> = {
  R: "bg-emerald-50 text-emerald-800", D: "bg-orange-50 text-orange-800", T: "bg-sky-50 text-sky-800",
  C: "bg-violet-50 text-violet-800",
};

function Montant({ m }: { m: MouvementFinance }) {
  return (
    <span className={`tabular-nums font-semibold whitespace-nowrap ${m.montant_signe < 0 ? "text-red-700" : "text-emerald-700"}`}>
      {m.montant_signe < 0 ? "−" : "+"} {formatPrice(m.montant)}
    </span>
  );
}

function Chiffre({ libelle, montant, aide, accent }: { libelle: string; montant: number; aide: string; accent?: boolean }) {
  return (
    <div className={`rounded-2xl p-4 ${accent ? "bg-primary text-white" : "bg-white border border-gray-100"}`}>
      <p className={`text-xs font-semibold ${accent ? "text-white/80" : "text-muted"}`}>{libelle}</p>
      <p className="font-heading font-bold text-xl mt-1 tabular-nums">{formatPrice(montant)}</p>
      <p className={`text-xs mt-0.5 ${accent ? "text-white/80" : "text-muted"}`}>{aide}</p>
    </div>
  );
}

/**
 * The ledger at a glance (module finance): the invariants that must always hold, the three balances that never mix
 * (Kwa-Ba's revenue, money owed to partners and travellers, deposits held), the sums owed by partner and the latest
 * lines. Every figure is read from the ledger, none is computed again from the bookings.
 */
export default function GrandLivre() {
  const { data: d, isLoading, isError, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ["admin", "finance", "grand-livre"], queryFn: lireGrandLivre,
  });
  const anomalies = d?.invariants.filter((i) => i.anomalies > 0) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        {d && (
          <p className="text-sm text-muted">
            Lu le {formatDate(new Date(dataUpdatedAt).toISOString())} à {new Date(dataUpdatedAt).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}
        <button onClick={() => refetch()} disabled={isFetching} className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-semibold disabled:opacity-50 sm:ml-auto">
          <RefreshCw size={16} aria-hidden className={isFetching ? "animate-spin" : ""} /> Actualiser
        </button>
      </div>

      {isLoading && <div className="h-64 skeleton rounded-2xl" />}
      {isError && <p className="text-sm text-red-700">Impossible de lire le grand livre.</p>}
      {d && (
        <>
          <section className={`rounded-2xl border p-5 ${anomalies.length ? "border-red-200 bg-red-50" : "border-emerald-200 bg-emerald-50"}`}>
            <div className="flex items-center gap-2 mb-3">
              {anomalies.length
                ? <TriangleAlert size={20} className="text-red-700" aria-hidden />
                : <CheckCircle2 size={20} className="text-emerald-700" aria-hidden />}
              <h2 className="font-heading font-bold text-dark">
                {anomalies.length ? `${anomalies.length} invariant${anomalies.length > 1 ? "s" : ""} en anomalie` : "Tous les invariants sont respectés"}
              </h2>
            </div>
            <ul className="grid sm:grid-cols-2 gap-2 text-sm">
              {d.invariants.map((i) => (
                <li key={i.invariant} className={`flex items-start justify-between gap-3 rounded-xl px-3 py-2 ${i.anomalies ? "bg-white text-red-800 font-semibold" : "bg-white/70 text-dark"}`}>
                  <span><span className="text-muted font-normal">{i.invariant}</span> · {i.libelle}</span>
                  <span className="tabular-nums whitespace-nowrap">{i.anomalies ? `${i.anomalies} anomalie${i.anomalies > 1 ? "s" : ""}` : "OK"}</span>
                </li>
              ))}
            </ul>
          </section>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Chiffre libelle="Revenu Kwa-Ba du mois" montant={d.soldes.revenu_du_mois} aide="Frais de service et commissions acquises" accent />
            <Chiffre libelle="Dû aux partenaires" montant={d.soldes.du_partenaires} aide="Fonds de tiers : jamais à Kwa-Ba" />
            <Chiffre libelle="Dû aux voyageurs" montant={d.soldes.du_voyageurs} aide="Remboursements décidés, pas encore envoyés" />
            <Chiffre libelle="Cautions détenues" montant={d.soldes.cautions_detenues} aide="Argent des voyageurs, à restituer" />
          </div>
          {Object.keys(d.soldes.comptes).length > 0 && (
            <p className="text-sm text-muted">
              Solde au grand livre : {Object.entries(d.soldes.comptes).map(([c, m]) => `${c === "FEDAPAY" ? "FedaPay" : c} ${formatPrice(m)}`).join(" · ")}
            </p>
          )}

          <section className="bg-white rounded-2xl border border-gray-100 p-5">
            <h2 className="font-heading font-bold text-dark mb-3">Sommes dues, par partenaire</h2>
            {d.du_aux_partenaires.length === 0 ? <p className="text-sm text-muted">Kwa-Ba ne doit rien à personne.</p> : (
              <ul className="divide-y divide-gray-50 text-sm">
                {d.du_aux_partenaires.map((p) => (
                  <li key={`${p.tiers_type}-${p.tiers_id}`} className="flex flex-wrap justify-between gap-2 py-2">
                    <span className="min-w-0">
                      <strong className="text-dark">{p.nom || p.tiers_id || "À désigner"}</strong> <span className="text-muted">· {TIERS[p.tiers_type] ?? p.tiers_type}</span>
                      {p.email && <span className="block text-xs text-muted break-all">{p.email}</span>}
                    </span>
                    <span className={`tabular-nums font-semibold ${p.solde_du < 0 ? "text-red-700" : "text-dark"}`}>{formatPrice(p.solde_du)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="bg-white rounded-2xl border border-gray-100 overflow-x-auto">
            <h2 className="font-heading font-bold text-dark px-5 pt-5">Dernières lignes du grand livre</h2>
            <p className="text-xs text-muted px-5 mb-3">Une ligne écrite ne se modifie jamais : une erreur se corrige par une ligne inverse.</p>
            {/* Phone: one card per line, the amount always in view */}
            <ul className="sm:hidden divide-y divide-gray-50 text-sm">
              {d.mouvements.length === 0 && <li className="px-5 py-4 text-muted">Aucune ligne pour l&apos;instant.</li>}
              {d.mouvements.map((m) => (
                <li key={m.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <span className="min-w-0">
                      <span className={`inline-block rounded-md px-1.5 py-0.5 text-xs font-bold mr-1.5 ${FAMILLES[m.famille] ?? "bg-gray-100 text-dark"}`}>{m.nature_code}</span>
                      {m.nature_libelle}
                    </span>
                    <Montant m={m} />
                  </div>
                  <p className="text-xs text-muted mt-1">
                    N° {m.id} · {formatDate(m.date_evenement)} · {OFFRES[m.offre_code] ?? m.offre_code}
                    {m.piece_reference && <> · {m.piece_reference}</>}
                  </p>
                  <p className="text-xs text-muted">
                    {m.tiers_type ? `${m.nom || m.tiers_id || "À désigner"} · ${TIERS[m.tiers_type] ?? m.tiers_type}` : "Kwa-Ba"}
                    {m.annule_mouvement_id && <> · corrige la ligne {m.annule_mouvement_id}</>}
                  </p>
                </li>
              ))}
            </ul>
            <table className="hidden sm:table w-full text-sm">
              <thead><tr className="text-left text-xs text-muted border-b border-gray-100">
                <th className="px-5 py-2 font-semibold">N°</th><th className="px-3 py-2 font-semibold">Date</th>
                <th className="px-3 py-2 font-semibold">Nature</th><th className="px-3 py-2 font-semibold">Offre</th>
                <th className="px-3 py-2 font-semibold">Tiers</th><th className="px-3 py-2 font-semibold">Pièce</th>
                <th className="px-5 py-2 font-semibold text-right">Montant</th>
              </tr></thead>
              <tbody>
                {d.mouvements.length === 0 && <tr><td colSpan={7} className="px-5 py-4 text-muted">Aucune ligne pour l&apos;instant.</td></tr>}
                {d.mouvements.map((m) => (
                  <tr key={m.id} className="border-b border-gray-50 last:border-0 align-top">
                    <td className="px-5 py-2 text-muted tabular-nums">{m.id}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatDate(m.date_evenement)}</td>
                    <td className="px-3 py-2">
                      <span className={`inline-block rounded-md px-1.5 py-0.5 text-xs font-bold mr-1.5 ${FAMILLES[m.famille] ?? "bg-gray-100 text-dark"}`}>{m.nature_code}</span>
                      {m.nature_libelle}
                      {m.annule_mouvement_id && <span className="block text-xs text-muted">Corrige la ligne {m.annule_mouvement_id}</span>}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">{OFFRES[m.offre_code] ?? m.offre_code}</td>
                    <td className="px-3 py-2">{m.tiers_type ? <>{m.nom || m.tiers_id || "À désigner"} <span className="text-muted">· {TIERS[m.tiers_type] ?? m.tiers_type}</span></> : <span className="text-muted">Kwa-Ba</span>}</td>
                    <td className="px-3 py-2 text-muted whitespace-nowrap">{m.piece_reference ?? "—"}</td>
                    <td className="px-5 py-2 text-right"><Montant m={m} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}
