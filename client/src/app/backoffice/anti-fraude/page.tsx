"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import Select from "@/components/ui/Select";
import type { AlerteFraude } from "@/types/api/admin";

const STATUTS = [{ value: "a_traiter", label: "À traiter" }, { value: "traitees", label: "Traitées" }, { value: "toutes", label: "Toutes" }];

/** Bypass attempts: contact details or off-site payment offered in a message or a listing. */
export default function AntiFraudePage() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [statut, setStatut] = useState("a_traiter");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AlerteFraude>("anti-fraude", { q: recherche, statut });
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);

  const colonnes: Colonne<AlerteFraude>[] = [
    {
      titre: "Compte", masquerMobile: true, cellule: (a) => (
        <div className="text-xs min-w-0">
          <Link href={`/backoffice/utilisateurs?q=${encodeURIComponent(a.utilisateur.email)}`} className="text-dark font-semibold hover:text-primary truncate block">
            {a.utilisateur.nom}
          </Link>
          <p className="text-muted truncate">{a.utilisateur.email} · {a.utilisateur.role}</p>
          {(a.utilisateur.nb_alertes ?? 0) > 1 && <p className="text-red-700 font-semibold">{a.utilisateur.nb_alertes} alertes au total</p>}
        </div>
      ),
    },
    {
      titre: "Détecté", cellule: (a) => (
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap gap-1">{a.types.map((t) => <Pill key={t} ton={t.startsWith("Paiement") ? "rouge" : "orange"}>{t}</Pill>)}</div>
          <p className="text-xs font-mono text-muted break-all">{a.extraits.join(" · ")}</p>
        </div>
      ),
    },
    {
      titre: "Où", cellule: (a) => (
        <div className="text-xs">
          <p className="text-dark">{a.contexte_libelle}</p>
          <p className="text-muted">{formatDate(a.cree_le, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>
          <p className="text-muted">{a.masquee ? "Masqué automatiquement" : "Signalé (non masqué)"}</p>
        </div>
      ),
    },
    {
      titre: "Statut", cellule: (a) => a.traitee
        ? <div className="text-xs"><Pill ton="vert">Traitée</Pill>{a.note && <p className="text-muted mt-1 max-w-[220px]">{a.note}</p>}</div>
        : <Pill ton="orange">À traiter</Pill>,
    },
  ];

  const actions = (a: AlerteFraude) => a.traitee ? null : (
    <ActionButton onClick={() => setConfirmation({
      titre: "Marquer l'alerte comme traitée",
      message: <>Indiquez ce qui a été fait pour <strong>{a.utilisateur.nom}</strong> (avertissement, compte suspendu depuis Utilisateurs…).</>,
      libelle: "Marquer traitée", motif: true,
      action: async (note) => {
        try {
          await api.post(`/v1/admin/anti-fraude/${a.id}/traiter/`, { note });
          toast.success("Alerte traitée");
          queryClient.invalidateQueries({ queryKey: ["admin", "anti-fraude"] });
        } catch (err) {
          toast.error(apiErrorMessage(err));
          throw err;
        }
      },
    })}>Traiter</ActionButton>
  );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Anti-fraude</h1>
        <p className="text-muted text-sm mt-1">
          Coordonnées ou paiement hors site proposés dans les messages et les annonces. Les coordonnées sont masquées automatiquement ;
          l&apos;administrateur prévient ou suspend les comptes qui insistent (alerte par email dès 3 tentatives en 30 jours).
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Nom ou email" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="sm:w-44" />
      </div>
      {data?.count === 0 && statut === "a_traiter" && !recherche ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center">
          <ShieldCheck size={36} className="mx-auto text-secondary" aria-hidden />
          <p className="mt-3 font-semibold text-dark">Aucune alerte à traiter</p>
        </div>
      ) : (
        <AdminTable colonnes={colonnes} lignes={data?.results} cle={(a) => String(a.id)} titreMobile={(a) => colonnes[0].cellule(a)} actions={actions}
          chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      )}
      {data && data.count > 0 && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}
