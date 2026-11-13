"use client";

import { traiterAlerteFraude } from "@/features/messaging";
import { useCallback, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import Select from "@/components/ui/Select";
import type { AlerteFraude } from "@/types/api/admin";
import { ReportPanel, SanctionPanel } from "./ModerationPanels";

const STATUTS = [{ value: "a_traiter", label: "À traiter" }, { value: "traitees", label: "Traitées" }, { value: "toutes", label: "Toutes" }];
const KINDS = [
  { value: "", label: "Toutes" },
  { value: "bypass", label: "Contournement" },
  { value: "report", label: "Signalements" },
  { value: "refusal", label: "Messages refusés" },
  { value: "simulated", label: "Refus simulés" },
  { value: "warning_ignored", label: "Envoyés après avertissement" },
  { value: "false_positive", label: "Blocages contestés" },
  { value: "contest", label: "Contestations" },
  { value: "sanction", label: "Sanctions" },
  { value: "abusive_reporter", label: "Signalements rejetés" },
];

/** Bypass attempts: contact details or off-site payment offered in a message or a listing. */
export default function AntiFraudePage() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [statut, setStatut] = useState("a_traiter");
  const [kind, setKind] = useState("");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AlerteFraude>("anti-fraude", { q: recherche, statut, kind });
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [reportId, setReportId] = useState<number | null>(null);
  const [sanctionId, setSanctionId] = useState<number | null>(null);
  const closePanels = useCallback(() => { setReportId(null); setSanctionId(null); }, []);
  const panelDone = useCallback(() => {
    closePanels();
    queryClient.invalidateQueries({ queryKey: ["admin", "anti-fraude"] });
  }, [closePanels, queryClient]);

  const colonnes: Colonne<AlerteFraude>[] = [
    {
      titre: "Compte", masquerMobile: true, cellule: (a) => (
        <div className="text-xs min-w-0">
          <Link href={`/backoffice/utilisateurs?q=${encodeURIComponent(a.utilisateur.email)}`} className="text-dark font-semibold hover:text-brand truncate block">
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
          <div className="flex flex-wrap gap-1">
            <Pill ton={a.simulee ? "bleu" : "gris"}>{a.kind_libelle}</Pill>
            {a.menace && <Pill ton="rouge">Menace</Pill>}
            {a.legal_hold && <Pill ton="bleu">Conservation prolongée</Pill>}
            {a.types.filter((t) => !(a.menace && t === "Menace")).map((t) => <Pill key={t} ton={t.startsWith("Paiement") ? "rouge" : "orange"}>{t}</Pill>)}
          </div>
          <p className="text-xs font-mono text-muted break-all">{a.extraits.join(" · ")}</p>
        </div>
      ),
    },
    {
      titre: "Où", cellule: (a) => (
        <div className="text-xs">
          <p className="text-dark">{a.contexte_libelle}</p>
          <p className="text-muted">{formatDate(a.cree_le, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>
          {a.kind === "bypass" && <p className="text-muted">{a.masquee ? "Masqué automatiquement" : "Signalé (non masqué)"}</p>}
          {a.kind === "simulated" && <p className="text-muted">Mode observation : message livré</p>}
        </div>
      ),
    },
    {
      titre: "Statut", cellule: (a) => a.traitee
        ? <div className="text-xs"><Pill ton="vert">Traitée</Pill>{a.note && <p className="text-muted mt-1 max-w-[220px]">{a.note}</p>}</div>
        : <Pill ton="orange">À traiter</Pill>,
    },
  ];

  const actions = (a: AlerteFraude) => {
    if (a.kind === "report") return <ActionButton onClick={() => setReportId(Number(a.objet_id))}>{a.traitee ? "Voir" : "Examiner"}</ActionButton>;
    if (a.kind === "sanction" || a.kind === "contest") {
      return <ActionButton onClick={() => setSanctionId(Number(a.objet_id))}>{a.kind === "contest" && !a.traitee ? "Examiner" : "Voir"}</ActionButton>;
    }
    return a.traitee ? null : treatButton(a);
  };

  const treatButton = (a: AlerteFraude) => (
    <ActionButton onClick={() => setConfirmation({
      titre: "Marquer l'alerte comme traitée",
      message: <>Indiquez ce qui a été fait pour <strong>{a.utilisateur.nom}</strong> (avertissement, compte suspendu depuis Utilisateurs…).</>,
      libelle: "Marquer traitée", motif: true,
      action: async (note) => {
        try {
          await traiterAlerteFraude(a.id, note);
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
        <p className="text-muted text-sm mt-1">
          Modération des messages : refus (réels ou simulés en mode observation), signalements à confirmer ou rejeter, sanctions et
          contestations. Seuls les signalements confirmés comptent dans l&apos;échelle de sanctions ; toute menace est signalée par email aussitôt.
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Nom ou email" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="sm:w-44" />
        <Select label="Nature" value={kind} onChange={setKind} options={KINDS} className="sm:w-56" />
      </div>
      {data?.count === 0 && statut === "a_traiter" && !recherche && !kind ? (
        <div className="bg-surface rounded-2xl border border-gray-100 p-8 text-center">
          <ShieldCheck size={36} className="mx-auto text-secondary" aria-hidden />
          <p className="mt-3 font-semibold text-dark">Aucune alerte à traiter</p>
        </div>
      ) : (
        <AdminTable colonnes={colonnes} lignes={data?.results} cle={(a) => String(a.id)} titreMobile={(a) => colonnes[0].cellule(a)} actions={actions}
          chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      )}
      {data && data.count > 0 && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
      {reportId !== null && <ReportPanel reportId={reportId} onClose={closePanels} onDone={panelDone} />}
      {sanctionId !== null && <SanctionPanel sanctionId={sanctionId} onClose={closePanels} onDone={panelDone} />}
    </div>
  );
}
