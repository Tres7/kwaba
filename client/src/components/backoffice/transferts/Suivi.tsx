"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import { BoutonFacture } from "@/features/documents";
import Panneau, { Champ, Liste, erreursApi } from "@/components/backoffice/Panneau";
import Select from "@/components/ui/Select";
import type { AdminTransfert } from "@/types/api/admin";

const STATUTS = [
  { value: "", label: "Tous les statuts" },
  { value: "confirme", label: "Payés, chauffeur à attribuer" },
  { value: "chauffeur_assigne", label: "Chauffeur attribué" },
  { value: "en_attente_paiement", label: "En attente de paiement" },
  { value: "termine", label: "Effectués" },
  { value: "annule", label: "Annulés" },
];
const TON: Record<AdminTransfert["statut"], "vert" | "orange" | "gris" | "rouge" | "bleu"> = {
  confirme: "orange", chauffeur_assigne: "vert", en_attente_paiement: "gris", termine: "bleu", annule: "rouge",
};
const dateHeure = (d: string) => formatDate(d, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function Suivi() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [statut, setStatut] = useState("confirme");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AdminTransfert>("transferts/transferts", { q: recherche, statut });
  const [attribution, setAttribution] = useState<AdminTransfert | null>(null);
  const [chauffeur, setChauffeur] = useState("");
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);

  const { data: chauffeurs = [] } = useQuery({
    queryKey: ["admin", "transferts", "chauffeurs-dispo", attribution?.id],
    queryFn: async () => (await api.get<{ id: number; nom: string; telephone: string; vehicule: string }[]>(`/v1/admin/transferts/transferts/${attribution!.id}/chauffeurs/`)).data,
    enabled: !!attribution,
  });

  const attribuer = async () => {
    if (!attribution) return;
    setEnvoi(true);
    try {
      await api.post(`/v1/admin/transferts/transferts/${attribution.id}/attribuer/`, { chauffeur: Number(chauffeur) });
      toast.success("Chauffeur attribué : le voyageur reçoit ses coordonnées");
      setAttribution(null);
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const colonnes: Colonne<AdminTransfert>[] = [
    { titre: "Transfert", masquerMobile: true, cellule: (t) => (
      <div className="min-w-0"><p className="font-semibold text-dark">{t.aeroport.ville} · vol {t.numero_vol}</p><p className="text-xs text-muted font-mono">{t.reference}</p></div>
    ) },
    { titre: "Arrivée", cellule: (t) => <div className="text-xs"><p className="text-dark">{dateHeure(t.arrivee)}</p>{t.majoration_nuit && <p className="text-muted">Tarif de nuit</p>}</div> },
    { titre: "Voyageur", cellule: (t) => <div className="text-xs"><p className="text-dark font-medium">{t.voyageur.nom}</p><p className="text-muted">{t.telephone}</p></div> },
    { titre: "Véhicule", cellule: (t) => <span className="text-xs">{t.categorie_libelle} · {t.passagers} pers. · {t.bagages} val.</span> },
    { titre: "Montant", cellule: (t) => <span className="tabular-nums whitespace-nowrap">{formatPrice(t.prix)}</span> },
    { titre: "Statut", cellule: (t) => <div className="flex flex-col items-start gap-1"><Pill ton={TON[t.statut]}>{t.statut_libelle}</Pill>
      {t.chauffeur && <span className="text-xs text-muted">{t.chauffeur.nom}</span>}</div> },
  ];

  const actions = (t: AdminTransfert) => (
    <>
      {["confirme", "chauffeur_assigne", "termine"].includes(t.statut) && <BoutonFacture objet="transfert" id={t.id} />}
      {(t.statut === "confirme" || t.statut === "chauffeur_assigne") && (
        <ActionButton onClick={() => { setAttribution(t); setChauffeur(t.chauffeur ? String(t.chauffeur.id) : ""); setErreurs({}); }}>
          {t.chauffeur ? "Changer de chauffeur" : "Attribuer"}
        </ActionButton>
      )}
      {(t.statut === "confirme" || t.statut === "chauffeur_assigne" || t.statut === "en_attente_paiement") && (
        <ActionButton danger onClick={() => setConfirmation({
          titre: "Annuler le transfert", danger: true, motif: true, libelle: "Annuler et rembourser",
          message: <>Le transfert <strong>{t.reference}</strong> sera annulé et le voyageur remboursé intégralement s&apos;il a payé.</>,
          action: async (motif) => {
            try {
              await api.post(`/v1/admin/transferts/transferts/${t.id}/annuler/`, { motif });
              toast.success("Transfert annulé");
              queryClient.invalidateQueries({ queryKey: ["admin"] });
            } catch (err) {
              toast.error(apiErrorMessage(err));
              throw err;
            }
          },
        })}>Annuler</ActionButton>
      )}
    </>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Référence, email, téléphone ou n° de vol" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="sm:w-64" />
      </div>
      <AdminTable colonnes={colonnes} lignes={data?.results} cle={(t) => t.id} titreMobile={(t) => colonnes[0].cellule(t)} actions={actions}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}

      <Panneau ouvert={!!attribution} titre="Attribuer un chauffeur" onFermer={() => setAttribution(null)} onValider={attribuer} envoi={envoi} libelle="Attribuer">
        {attribution && (
          <div className="text-sm bg-light-muted rounded-xl p-3 space-y-1">
            <p className="font-semibold text-dark">{attribution.aeroport.ville} · vol {attribution.numero_vol} · {dateHeure(attribution.arrivee)}</p>
            <p className="text-gray-600">{attribution.categorie_libelle} · {attribution.passagers} passager(s) · {attribution.bagages} valise(s)</p>
            <p className="text-gray-600">Destination : {attribution.destination}</p>
            {attribution.message && <p className="text-gray-600 italic">« {attribution.message} »</p>}
          </div>
        )}
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <Champ label="Chauffeur" erreur={erreurs.chauffeur} aide={chauffeurs.length ? "Chauffeurs de cet aéroport dont le véhicule convient" : "Aucun chauffeur actif de cet aéroport n'a un véhicule assez grand."}>
          <Liste value={chauffeur} onChange={(e) => setChauffeur(e.target.value)} required
            options={[{ value: "", label: "Choisir" }, ...chauffeurs.map((c) => ({ value: String(c.id), label: `${c.nom} · ${c.vehicule} · ${c.telephone}` }))]} />
        </Champ>
      </Panneau>
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}
