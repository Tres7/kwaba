"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import BoutonFacture from "@/features/documents/admin/BoutonFacture";
import DateRangeField from "@/components/ui/DateRangeField";
import Select from "@/components/ui/Select";
import type { AdminReservation } from "@/types/api/admin";

const STATUTS = [
  { value: "", label: "Tous les statuts" },
  { value: "confirmed", label: "Confirmées" },
  { value: "pending", label: "En attente" },
  { value: "cancelled", label: "Annulées" },
];
const STATUT_PILL = {
  confirmed: { ton: "vert", label: "Confirmée" },
  pending: { ton: "orange", label: "En attente" },
  cancelled: { ton: "rouge", label: "Annulée" },
} as const;
const PAIEMENT: Record<string, string> = { mobile_money: "Mobile Money", carte: "Carte", paypal: "PayPal" };

function Reservations() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [statut, setStatut] = useState(searchParams.get("statut") ?? "");
  const [debut, setDebut] = useState("");
  const [fin, setFin] = useState("");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const recherche = useDebounced(q);

  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AdminReservation>(
    "reservations", { q: recherche, statut, debut: debut && fin ? debut : "", fin: debut && fin ? fin : "" },
  );

  const colonnes: Colonne<AdminReservation>[] = [
    {
      titre: "Réservation", masquerMobile: true,
      cellule: (r) => (
        <div className="min-w-0">
          <p className="font-semibold text-dark truncate">{r.hebergement.name}</p>
          <p className="text-xs text-muted font-mono">{r.reference}</p>
        </div>
      ),
    },
    { titre: "Voyageur", cellule: (r) => <div className="text-xs min-w-0"><p className="text-dark font-medium truncate">{r.voyageur.nom}</p><p className="text-muted truncate">{r.voyageur.email}</p></div> },
    { titre: "Séjour", cellule: (r) => <span className="text-xs whitespace-nowrap">{formatDate(r.check_in, { day: "numeric", month: "short" })} → {formatDate(r.check_out)} · {r.nights} n.</span> },
    { titre: "Montant", cellule: (r) => <div className="text-right md:text-left"><p className="tabular-nums whitespace-nowrap font-medium">{formatPrice(r.total_price)}</p><p className="text-xs text-muted">{PAIEMENT[r.payment_method]}</p></div> },
    { titre: "Statut", cellule: (r) => <Pill ton={STATUT_PILL[r.status].ton}>{STATUT_PILL[r.status].label}</Pill> },
  ];

  const actions = (r: AdminReservation) =>
    r.status === "cancelled" ? null : (
      <>
      {r.status === "confirmed" && <BoutonFacture objet="reservation" id={r.id} />}
      <ActionButton danger onClick={() => setConfirmation({
        titre: "Annuler la réservation",
        message: <>Annuler <strong>{r.reference}</strong> ({r.voyageur.nom}, {r.hebergement.name}) ? Le voyageur et l&apos;hôte ne pourront pas la rétablir.</>,
        libelle: "Annuler la réservation", danger: true, motif: true,
        action: async (motif) => {
          try {
            await api.post(`/v1/admin/reservations/${r.id}/annuler/`, { motif });
            toast.success("Réservation annulée");
            queryClient.invalidateQueries({ queryKey: ["admin"] });
          } catch (err) {
            toast.error(apiErrorMessage(err));
            throw err;
          }
        },
      })}>Annuler</ActionButton>
      </>
    );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Réservations</h1>
        <p className="text-muted text-sm mt-1">{data ? `${data.count} réservation${data.count > 1 ? "s" : ""}` : "…"}</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Référence, annonce ou email du voyageur" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="lg:w-48" />
        <DateRangeField checkIn={debut} checkOut={fin} onChange={(a, d) => { setDebut(a); setFin(d); }} className="lg:w-80" />
        {(debut || fin) && <button onClick={() => { setDebut(""); setFin(""); }} className="text-sm font-semibold text-muted hover:text-dark">Toutes les dates</button>}
      </div>

      <AdminTable
        colonnes={colonnes} lignes={data?.results} cle={(r) => r.id} actions={actions}
        titreMobile={(r) => colonnes[0].cellule(r)}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch}
      />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}

export default function ReservationsAdminPage() {
  return <Suspense><Reservations /></Suspense>;
}
