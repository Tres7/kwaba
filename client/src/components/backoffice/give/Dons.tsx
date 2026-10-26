"use client";

import { useState } from "react";
import { formatDate, formatPrice } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import Select from "@/components/ui/Select";
import type { DonAdmin } from "@/types/api/admin";

const STATUTS = [{ value: "paye", label: "Payés" }, { value: "en_attente", label: "En attente" }, { value: "echoue", label: "Non aboutis" }, { value: "", label: "Tous" }];

/** Donations received (read only): transfers to the NGOs are made from the Transfers tab. */
export default function Dons() {
  const [q, setQ] = useState("");
  const [statut, setStatut] = useState("paye");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<DonAdmin>("give/dons", { q: recherche, statut });

  const colonnes: Colonne<DonAdmin>[] = [
    { titre: "Don", masquerMobile: true, cellule: (d) => <div><p className="font-semibold text-dark">{d.organisation}</p><p className="text-xs text-muted">{d.projet ?? "Don libre"} · {d.reference}</p></div> },
    { titre: "Donateur", cellule: (d) => <div className="text-xs"><p className="text-dark font-medium">{d.donateur.nom}</p><p className="text-muted">{d.donateur.email}</p></div> },
    { titre: "Montant", cellule: (d) => <div className="text-xs tabular-nums"><p className="text-dark font-semibold">{formatPrice(d.montant_ong)} pour l&apos;ONG</p><p className="text-muted">débité {formatPrice(d.total)}</p></div> },
    { titre: "Date", cellule: (d) => <span className="text-xs">{formatDate(d.paye_le ?? d.cree_le)}</span> },
    { titre: "Statut", cellule: (d) => <Pill ton={d.statut === "paye" ? "vert" : d.statut === "echoue" ? "rouge" : "gris"}>{d.statut_libelle}</Pill> },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Email du donateur" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="sm:w-48" />
      </div>
      <AdminTable colonnes={colonnes} lignes={data?.results} cle={(d) => d.id} titreMobile={(d) => colonnes[0].cellule(d)}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}
    </div>
  );
}
