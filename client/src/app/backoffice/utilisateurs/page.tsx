"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQueryClient } from "@tanstack/react-query";
import { BadgeCheck } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { formatDate, initials, ROLE_LABELS } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConditionsHote from "@/components/backoffice/ConditionsHote";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import Select from "@/components/ui/Select";
import type { AdminUser, Role } from "@/types/api/admin";

const ROLES: { value: "" | Role; label: string }[] = [
  { value: "", label: "Tous les rôles" },
  { value: "voyageur", label: "Voyageurs" },
  { value: "hote", label: "Hôtes" },
  { value: "agent", label: "Agents de terrain" },
  { value: "admin", label: "Administrateurs" },
];
const STATUTS = [
  { value: "", label: "Tous les statuts" },
  { value: "true", label: "Actifs" },
  { value: "false", label: "Désactivés" },
];

function Utilisateurs() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: session } = useSession();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [role, setRole] = useState<"" | Role>((searchParams.get("role") as Role) ?? "");
  const [actif, setActif] = useState(searchParams.get("actif") ?? "");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [conditions, setConditions] = useState<AdminUser | null>(null);
  const recherche = useDebounced(q);

  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AdminUser>("users", { q: recherche, role, actif });

  const modifier = async (u: AdminUser, patch: Partial<Pick<AdminUser, "is_active" | "role">>, succes: string) => {
    try {
      await api.patch(`/v1/admin/users/${u.id}/`, patch);
      toast.success(succes);
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    } catch (err) {
      toast.error(apiErrorMessage(err));
      throw err;
    }
  };

  const nom = (u: AdminUser) => `${u.first_name} ${u.last_name}`.trim() || u.email;

  const colonnes: Colonne<AdminUser>[] = [
    {
      titre: "Utilisateur", masquerMobile: true,
      cellule: (u) => (
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0 overflow-hidden">
            {u.avatar_url ? <img src={u.avatar_url} alt="" className="w-full h-full object-cover" /> : initials(nom(u))}
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-dark truncate flex items-center gap-1">{nom(u)} {u.is_verified && <BadgeCheck size={14} className="text-secondary flex-shrink-0" aria-label="Email vérifié" />}</p>
            <p className="text-xs text-muted truncate">{u.email}</p>
          </div>
        </div>
      ),
    },
    { titre: "Rôle", cellule: (u) => <Pill ton={u.role === "admin" || u.role === "agent" ? "bleu" : u.role === "hote" ? "orange" : "gris"}>{ROLE_LABELS[u.role]}</Pill> },
    { titre: "Statut", cellule: (u) => <Pill ton={u.is_active ? "vert" : "rouge"}>{u.is_active ? "Actif" : "Désactivé"}</Pill> },
    {
      titre: "Commission", masquerMobile: true,
      cellule: (u) => u.conditions ? (
        <span className="text-xs text-gray-600 whitespace-nowrap">
          {u.conditions.commission_pourcent} %{u.conditions.categorie === "hotel" ? " · hôtel" : u.conditions.fondateur_fin ? ` · fondateur jusqu'au ${formatDate(u.conditions.fondateur_fin)}` : ""}
        </span>
      ) : <span className="text-xs text-muted">-</span>,
    },
    { titre: "Activité", cellule: (u) => <span className="text-xs text-gray-600 whitespace-nowrap">{u.nb_reservations} rés. · {u.nb_annonces} annonce{u.nb_annonces > 1 ? "s" : ""}</span> },
    { titre: "Inscrit le", cellule: (u) => <span className="text-xs text-gray-600 whitespace-nowrap">{formatDate(u.date_joined)}</span> },
  ];

  const actions = (u: AdminUser) => {
    if (u.id === session?.user?.id) return <span className="text-xs text-muted">Votre compte</span>;
    return (
      <>
        <Select
          label={`Rôle de ${nom(u)}`} value={u.role} className="w-44" buttonClassName="py-1.5 px-3 rounded-lg"
          options={(["voyageur", "hote", "agent", "admin"] as Role[]).map((r) => ({ value: r, label: ROLE_LABELS[r] }))}
          onChange={(r) => {
            if (r === u.role) return;
            setConfirmation({
              titre: "Changer le rôle",
              message: <>Passer <strong>{nom(u)}</strong> de « {ROLE_LABELS[u.role]} » à « {ROLE_LABELS[r]} » ?{r === "admin" && " Il aura accès au back-office."}{r === "agent" && " Il pourra vérifier les logements et les pièces d'identité des hôtes."}</>,
              libelle: "Changer le rôle",
              danger: r === "admin",
              action: () => modifier(u, { role: r }, "Rôle mis à jour"),
            });
          }}
        />
        {u.role === "hote" && <ActionButton onClick={() => setConditions(u)}>Commission</ActionButton>}
        {u.is_active ? (
          <ActionButton danger onClick={() => setConfirmation({
            titre: "Désactiver le compte",
            message: <><strong>{nom(u)}</strong> ne pourra plus se connecter. Ses réservations et annonces sont conservées.</>,
            libelle: "Désactiver", danger: true,
            action: () => modifier(u, { is_active: false }, "Compte désactivé"),
          })}>Désactiver</ActionButton>
        ) : (
          <ActionButton onClick={() => setConfirmation({
            titre: "Réactiver le compte", message: <><strong>{nom(u)}</strong> pourra de nouveau se connecter.</>,
            libelle: "Réactiver", action: () => modifier(u, { is_active: true }, "Compte réactivé"),
          })}>Réactiver</ActionButton>
        )}
      </>
    );
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Utilisateurs</h1>
        <p className="text-muted text-sm mt-1">{data ? `${data.count} compte${data.count > 1 ? "s" : ""}` : "…"}</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Nom, email ou téléphone" />
        <Select label="Rôle" value={role} onChange={setRole} options={ROLES} className="sm:w-48" />
        <Select label="Statut" value={actif} onChange={setActif} options={STATUTS} className="sm:w-48" />
      </div>

      <AdminTable
        colonnes={colonnes} lignes={data?.results} cle={(u) => u.id} actions={actions}
        titreMobile={(u) => colonnes[0].cellule(u)}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch}
      />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
      <ConditionsHote key={conditions?.id ?? "aucun"} hote={conditions} onFermer={() => setConditions(null)} />
    </div>
  );
}

export default function UtilisateursPage() {
  return <Suspense><Utilisateurs /></Suspense>;
}
