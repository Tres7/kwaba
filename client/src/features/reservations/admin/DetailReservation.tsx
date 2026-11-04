"use client";

import { useQuery } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import Panneau from "@/components/backoffice/Panneau";
import { formatDate, formatPrice } from "@/lib/utils";
import { lireReservationAdmin } from "../api";

const STATUTS: Record<string, string> = {
  reussi: "Réussi", en_attente: "En attente", echoue: "Échoué", annule: "Annulé",
  planifie: "Planifié", en_cours: "En cours", envoye: "Envoyé", attente_numero: "Numéro attendu", a_envoyer: "À envoyer",
};
const ANNULE_PAR: Record<string, string> = { voyageur: "le voyageur", hote: "l'hôte", plateforme: "Kwa-Ba", expiration: "expiration du paiement" };

function Ligne({ libelle, montant, fort, moins }: { libelle: string; montant: number; fort?: boolean; moins?: boolean }) {
  return (
    <div className={`flex justify-between gap-3 py-1.5 text-sm ${fort ? "font-bold text-dark border-t border-gray-100 mt-1 pt-2.5" : "text-gray-700"}`}>
      <span>{libelle}</span>
      <span className={`tabular-nums whitespace-nowrap ${moins ? "text-secondary" : ""}`}>{moins ? "− " : ""}{formatPrice(montant)}</span>
    </div>
  );
}

function Bloc({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-gray-100 p-4">
      <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">{titre}</h3>
      {children}
    </section>
  );
}

/** A booking opened from the back-office list: its stay, how its price splits and where the money went (AN-B3). */
export default function DetailReservation({ id, onFermer }: { id: string | null; onFermer: () => void }) {
  const { data: r, isLoading, isError } = useQuery({
    queryKey: ["admin", "reservation", id], queryFn: () => lireReservationAdmin(id as string), enabled: !!id,
  });
  const m = r?.montants;
  return (
    <Panneau ouvert={!!id} titre={r ? `Réservation ${r.reference}` : "Réservation"} onFermer={onFermer}>
      {isLoading && <div className="h-64 skeleton rounded-2xl" />}
      {isError && <p className="text-sm text-red-700">Impossible de lire cette réservation.</p>}
      {r && m && (
        <>
          <Bloc titre="Séjour">
            <p className="font-semibold text-dark">{r.hebergement.name} <span className="font-normal text-muted">· {r.hebergement.city}</span></p>
            <p className="text-sm text-gray-700 mt-1">
              {formatDate(r.check_in)} → {formatDate(r.check_out)} · {r.nights} nuit{r.nights > 1 ? "s" : ""} · {r.guests_count} voyageur{r.guests_count > 1 ? "s" : ""}
              {r.type_logement_nom && <> · {r.nb_unites > 1 ? `${r.nb_unites} × ` : ""}{r.type_logement_nom}</>}
            </p>
            <p className="text-sm text-gray-700 mt-1">Voyageur : {r.voyageur.nom} ({r.voyageur.email}) · Hôte : {r.hote.nom}</p>
            <p className="text-xs text-muted mt-1">Réservée le {formatDate(r.created_at)}{r.annule_le && ` · annulée le ${formatDate(r.annule_le)}${r.annule_par ? ` par ${ANNULE_PAR[r.annule_par] ?? r.annule_par}` : ""}`}</p>
          </Bloc>

          <Bloc titre="Le voyageur paie">
            <Ligne libelle={`${formatPrice(r.prix_nuit_reserve)} × ${r.nights} nuit${r.nights > 1 ? "s" : ""}${r.nb_unites > 1 ? ` × ${r.nb_unites}` : ""}`} montant={m.prix_nuits} />
            <Ligne libelle={`Frais de service (${m.taux_frais} %)`} montant={m.frais_service} />
            {m.frais_menage > 0 && <Ligne libelle="Frais de ménage" montant={m.frais_menage} />}
            <Ligne libelle="Total" montant={m.total} fort />
            {r.prix_nuit_actuel != null && r.prix_nuit_actuel !== r.prix_nuit_reserve && (
              <p className="flex items-start gap-1.5 text-xs text-amber-800 bg-amber-50 rounded-lg px-2.5 py-2 mt-2">
                <TriangleAlert size={14} className="flex-shrink-0 mt-px" aria-hidden />
                Prix de l&apos;annonce aujourd&apos;hui : {formatPrice(r.prix_nuit_actuel)} la nuit. La réservation garde le prix du jour où elle a été faite.
              </p>
            )}
            {!r.montants_figes && <p className="text-xs text-muted mt-2">Réservation antérieure au paiement en ligne : montants recalculés.</p>}
          </Bloc>

          <Bloc titre="Répartition">
            <Ligne libelle="Nuits" montant={m.prix_nuits} />
            <Ligne libelle={`Commission hôte (${m.taux_commission} %)`} montant={m.commission_hote} moins />
            {m.frais_menage > 0 && <Ligne libelle="Ménage (pour l'hôte)" montant={m.frais_menage} />}
            <Ligne libelle="Part de l'hôte" montant={m.montant_hote} fort />
            <Ligne libelle="Revenu Kwa-Ba (frais + commission)" montant={m.revenu_kwaba} />
          </Bloc>

          <Bloc titre="Mouvements d'argent">
            {r.paiements.length === 0 && r.remboursements.length === 0 && !r.versement && (
              <p className="text-sm text-muted">Aucun paiement en ligne.</p>
            )}
            <ul className="space-y-2 text-sm">
              {r.paiements.map((p) => (
                <li key={p.id} className="flex justify-between gap-3">
                  <span>Paiement {p.reference} · {p.prestataire}{p.mode ? ` (${p.mode})` : ""} · {formatDate(p.cree_le)}</span>
                  <span className="whitespace-nowrap tabular-nums">{formatPrice(p.montant)} · {STATUTS[p.statut] ?? p.statut}</span>
                </li>
              ))}
              {r.versement && (
                <li className="flex justify-between gap-3">
                  <span>Versement à l&apos;hôte · prévu le {formatDate(r.versement.date_prevue)}{r.versement.envoye_le ? `, envoyé le ${formatDate(r.versement.envoye_le)}` : ""}</span>
                  <span className="whitespace-nowrap tabular-nums">{formatPrice(r.versement.montant)} · {STATUTS[r.versement.statut] ?? r.versement.statut}</span>
                </li>
              )}
              {r.remboursements.map((rb) => (
                <li key={rb.id} className="flex justify-between gap-3">
                  <span>Remboursement · {rb.motif} · {formatDate(rb.cree_le)}</span>
                  <span className="whitespace-nowrap tabular-nums text-secondary">− {formatPrice(rb.montant)} · {STATUTS[rb.statut] ?? rb.statut}</span>
                </li>
              ))}
            </ul>
          </Bloc>
        </>
      )}
    </Panneau>
  );
}
