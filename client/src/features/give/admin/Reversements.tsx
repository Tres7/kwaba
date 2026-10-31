"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";
import { PAGE_SIZE, useAdminList } from "@/lib/useAdminList";
import { urlExterneSure } from "@/lib/url-sure";
import AdminTable, { ActionButton, Pagination, Pill, type Colonne } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Liste, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import Select from "@/components/ui/Select";
import type { ReversementAdmin } from "@/types/api/admin";
import { effectuerReversement, preparerReversements } from "../api";

const STATUTS = [{ value: "a_effectuer", label: "À effectuer" }, { value: "effectue", label: "Effectués" }, { value: "", label: "Tous" }];
const mois = (d: string) => formatDate(d, { month: "long", year: "numeric" });

export default function Reversements() {
  const queryClient = useQueryClient();
  const [statut, setStatut] = useState("a_effectuer");
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<ReversementAdmin>("give/reversements", { statut });
  const [cible, setCible] = useState<ReversementAdmin | null>(null);
  const [form, setForm] = useState({ moyen: "mobile_money", reference_operation: "", effectue_le: "", note: "" });
  const [preuve, setPreuve] = useState<File | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const preparer = async () => {
    try {
      const r = await preparerReversements();
      toast.success(r.dons ? `${r.dons} don(s) rattaché(s) à leur reversement` : "Rien à préparer : tous les dons des mois terminés sont déjà rattachés");
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const effectuer = async () => {
    if (!cible) return;
    setEnvoi(true);
    setErreurs({});
    const corps = new FormData();
    for (const [k, v] of Object.entries(form)) if (v) corps.append(k, v);
    if (preuve) corps.append("justificatif", preuve);
    try {
      await effectuerReversement(cible.id, corps);
      toast.success("Reversement effectué : la preuve est publiée sur la page de l'ONG");
      setCible(null);
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const colonnes: Colonne<ReversementAdmin>[] = [
    { titre: "ONG", masquerMobile: true, cellule: (r) => <div><p className="font-semibold text-dark">{r.organisation.nom}</p><p className="text-xs text-muted">Dons de {mois(r.periode)} · {r.reference}</p></div> },
    { titre: "Montant", cellule: (r) => <span className="tabular-nums whitespace-nowrap">{formatPrice(r.montant)} · {r.nb_dons} don(s)</span> },
    { titre: "Prévu le", cellule: (r) => <span className="text-xs">{formatDate(r.date_prevue)}</span> },
    { titre: "Statut", cellule: (r) => (
      <div className="flex flex-col items-start gap-1">
        <Pill ton={r.statut === "effectue" ? "vert" : "orange"}>{r.statut_libelle}</Pill>
        {urlExterneSure(r.justificatif) && <a href={urlExterneSure(r.justificatif)} target="_blank" rel="noreferrer" className="relative zone-tactile text-xs text-primary font-semibold inline-flex items-center gap-1">Preuve <ExternalLink size={11} /></a>}
      </div>
    ) },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="sm:w-56" />
        <button onClick={preparer} className="px-4 py-2.5 rounded-xl border border-gray-200 text-sm font-bold text-dark hover:bg-gray-50">Préparer les reversements du mois</button>
      </div>
      <AdminTable colonnes={colonnes} lignes={data?.results} cle={(r) => r.id} titreMobile={(r) => colonnes[0].cellule(r)}
        actions={(r) => r.statut === "a_effectuer" ? <ActionButton onClick={() => { setCible(r); setForm({ moyen: "mobile_money", reference_operation: "", effectue_le: "", note: "" }); setPreuve(null); setErreurs({}); }}>Marquer effectué</ActionButton> : null}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}

      <Panneau ouvert={!!cible} titre="Reversement effectué" onFermer={() => setCible(null)} onValider={effectuer} envoi={envoi} libelle="Valider">
        {cible && (
          <div className="text-sm bg-light-muted rounded-xl p-3 space-y-1">
            <p className="font-semibold text-dark">{formatPrice(cible.montant)} à {cible.organisation.nom}</p>
            <p className="text-gray-600">Dons de {mois(cible.periode)} ({cible.nb_dons})</p>
            <p className="text-gray-600 whitespace-pre-line">{cible.coordonnees_reversement || "Coordonnées de reversement à renseigner sur la fiche de l'ONG."}</p>
          </div>
        )}
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Moyen"><Liste value={form.moyen} onChange={(e) => setForm({ ...form, moyen: e.target.value })}
            options={[{ value: "mobile_money", label: "Mobile Money" }, { value: "virement", label: "Virement bancaire" }]} /></Champ>
          <Champ label="Date du virement" aide="Vide : aujourd'hui" erreur={erreurs.effectue_le}><Saisie type="date" value={form.effectue_le} onChange={(e) => setForm({ ...form, effectue_le: e.target.value })} /></Champ>
        </div>
        <Champ label="Référence de l'opération" erreur={erreurs.reference_operation}><Saisie value={form.reference_operation} onChange={(e) => setForm({ ...form, reference_operation: e.target.value })} required /></Champ>
        <Champ label="Preuve du virement (PDF ou image)" aide="Publiée sur la page de l'ONG : masquez les numéros de compte" erreur={erreurs.justificatif}>
          <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="text-sm" onChange={(e) => setPreuve(e.target.files?.[0] ?? null)} required />
        </Champ>
        <Champ label="Message public (facultatif)" aide="Ce que l'ONG a fait des fonds, par exemple"><Zone value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></Champ>
      </Panneau>
    </div>
  );
}
