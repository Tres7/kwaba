"use client";

import { annulerLocationAdmin, attribuerLocation, lireChoixAttribution, retenirCaution } from "../api";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import { BoutonFacture } from "@/features/documents";
import Panneau, { Champ, Liste, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import Select from "@/components/ui/Select";
import type { AdminLocation } from "@/types/api/admin";

const STATUTS = [
  { value: "", label: "Tous les statuts" },
  { value: "confirmee", label: "Payées, à attribuer" },
  { value: "partenaire_assigne", label: "Attribuées" },
  { value: "en_attente_paiement", label: "En attente de paiement" },
  { value: "terminee", label: "Terminées" },
  { value: "annulee", label: "Annulées" },
];
const TON: Record<AdminLocation["statut"], "vert" | "orange" | "gris" | "rouge" | "bleu"> = {
  confirmee: "orange", partenaire_assigne: "vert", en_attente_paiement: "gris", terminee: "bleu", annulee: "rouge",
};
const dateHeure = (d: string) => formatDate(d, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function Suivi() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [statut, setStatut] = useState("confirmee");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AdminLocation>("location/locations", { q: recherche, statut });
  const [attribution, setAttribution] = useState<AdminLocation | null>(null);
  const [form, setForm] = useState({ partenaire: "", chauffeur: "", vehicule: "", immatriculation: "" });
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [retenue, setRetenue] = useState<AdminLocation | null>(null);
  const [formRetenue, setFormRetenue] = useState({ montant: "", motif: "" });

  const { data: choix } = useQuery({
    queryKey: ["admin", "location", "attribution", attribution?.id],
    queryFn: () => lireChoixAttribution((attribution as AdminLocation).id),
    enabled: !!attribution,
  });
  const loueurs = choix?.partenaires ?? [];
  const chauffeurs = choix?.chauffeurs ?? [];

  const ouvrir = (l: AdminLocation) => {
    setAttribution(l);
    setForm({ partenaire: l.partenaire ? String(l.partenaire.id) : l.proprietaire_vehicule ? String(l.proprietaire_vehicule) : "",
      chauffeur: l.chauffeur_partenaire ? String(l.chauffeur_partenaire.id) : l.chauffeur_demande ? String(l.chauffeur_demande.id) : "",
      vehicule: l.vehicule, immatriculation: l.immatriculation });
    setErreurs({});
  };

  const attribuer = async () => {
    if (!attribution) return;
    setEnvoi(true);
    try {
      await attribuerLocation(attribution.id, {
        ...form, partenaire: form.partenaire ? Number(form.partenaire) : null, chauffeur: form.chauffeur ? Number(form.chauffeur) : null,
      });
      toast.success("Location attribuée : le voyageur reçoit les coordonnées");
      setAttribution(null);
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const ouvrirRetenue = (l: AdminLocation) => {
    setRetenue(l);
    setFormRetenue({ montant: l.caution_retenue ? String(l.caution_retenue) : "", motif: l.caution_motif });
    setErreurs({});
  };

  const retenir = async () => {
    if (!retenue) return;
    setEnvoi(true);
    try {
      await retenirCaution(retenue.id, { montant: Number(formRetenue.montant || 0), motif: formRetenue.motif });
      toast.success(Number(formRetenue.montant) > 0 ? "Retenue enregistrée : elle sera versée au propriétaire" : "Retenue annulée");
      setRetenue(null);
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const etatCaution = (l: AdminLocation) => {
    if (!l.caution_en_ligne) return l.caution ? `Caution ${formatPrice(l.caution)} réglée au propriétaire` : "";
    const retenueTexte = l.caution_retenue ? `, retenue ${formatPrice(l.caution_retenue)}` : "";
    return `Caution ${formatPrice(l.caution)} ${l.caution_restituee_le ? "réglée" : "gardée"}${retenueTexte}`;
  };

  const colonnes: Colonne<AdminLocation>[] = [
    { titre: "Location", masquerMobile: true, cellule: (l) => (
      <div className="min-w-0"><p className="font-semibold text-dark">{l.categorie} · {l.formule_libelle}</p><p className="text-xs text-muted font-mono">{l.reference}</p></div>
    ) },
    { titre: "Voyageur", cellule: (l) => <div className="text-xs"><p className="text-dark font-medium">{l.voyageur.nom}</p><p className="text-muted">{l.telephone}</p></div> },
    { titre: "Prise", cellule: (l) => <div className="text-xs"><p className="text-dark">{dateHeure(l.debut)}</p><p className="text-muted">{l.lieu_prise} · {l.jours} j</p></div> },
    { titre: "Montant", cellule: (l) => <div className="text-xs"><p className="tabular-nums whitespace-nowrap text-sm">{formatPrice(l.prix)}</p>
      {etatCaution(l) && <p className="text-muted">{etatCaution(l)}</p>}</div> },
    { titre: "Statut", cellule: (l) => <div className="flex flex-col items-start gap-1"><Pill ton={TON[l.statut]}>{l.statut_libelle}</Pill>
      {l.partenaire && <span className="text-xs text-muted">{l.partenaire.nom}</span>}
      {l.chauffeur_partenaire && <span className="text-xs text-muted">Chauffeur : {l.chauffeur_partenaire.nom}</span>}</div> },
  ];

  const actions = (l: AdminLocation) => (
    <>
      {["confirmee", "partenaire_assigne", "terminee"].includes(l.statut) && <BoutonFacture objet="location" id={l.id} />}
      {(l.statut === "confirmee" || l.statut === "partenaire_assigne") && (
        <ActionButton onClick={() => ouvrir(l)}>{l.statut === "partenaire_assigne" ? "Modifier l'attribution" : "Attribuer"}</ActionButton>
      )}
      {l.caution_en_ligne && !l.caution_restituee_le && l.statut === "partenaire_assigne" && new Date(l.debut) <= new Date() && (
        <ActionButton onClick={() => ouvrirRetenue(l)}>{l.caution_retenue ? "Modifier la retenue" : "Retenue sur la caution"}</ActionButton>
      )}
      {(l.statut === "confirmee" || l.statut === "partenaire_assigne" || l.statut === "en_attente_paiement") && (
        <ActionButton danger onClick={() => setConfirmation({
          titre: "Annuler la location", danger: true, motif: true, libelle: "Annuler et rembourser",
          message: <>La location <strong>{l.reference}</strong> sera annulée et le voyageur remboursé intégralement s&apos;il a payé{l.caution_en_ligne ? ", caution comprise" : ""}.</>,
          action: async (motif) => {
            try {
              await annulerLocationAdmin(l.id, motif);
              toast.success("Location annulée");
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
        <SearchInput value={q} onChange={setQ} placeholder="Référence, email, téléphone ou conducteur" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="sm:w-64" />
      </div>
      <AdminTable colonnes={colonnes} lignes={data?.results} cle={(l) => l.id} titreMobile={(l) => colonnes[0].cellule(l)} actions={actions}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}

      <Panneau ouvert={!!attribution} titre="Attribuer la location" onFermer={() => setAttribution(null)} onValider={attribuer} envoi={envoi} libelle="Attribuer">
        {attribution && (
          <div className="text-sm bg-light-muted rounded-xl p-3 space-y-1">
            <p className="font-semibold text-dark">{attribution.categorie} · {attribution.formule_libelle} · {attribution.passagers} passager(s)</p>
            <p className="text-gray-600">{dateHeure(attribution.debut)} → {dateHeure(attribution.fin)}</p>
            <p className="text-gray-600">{attribution.lieu_prise}{attribution.adresse_prise ? ` · ${attribution.adresse_prise}` : ""}</p>
            {attribution.precisions && <p className="text-gray-600 italic">« {attribution.precisions} »</p>}
            {attribution.conducteur && <p className="text-gray-600">Conducteur : {attribution.conducteur} · permis {attribution.permis_numero} ({attribution.permis_pays})</p>}
            {(attribution.jours_hors_lome > 0 || attribution.jours_hors_pays > 0) && (
              <p className="text-gray-600">Déplacements : {attribution.jours_hors_lome} j hors de Lomé, {attribution.jours_hors_pays} j hors du pays</p>
            )}
            {attribution.chauffeur_demande && <p className="text-secondary font-semibold">Chauffeur redemandé (« Mon chauffeur ») : {attribution.chauffeur_demande.nom}</p>}
          </div>
        )}
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        {attribution?.formule !== "chauffeur_seul" && (
          <>
            <Champ label="Propriétaire" erreur={erreurs.partenaire} aide={loueurs.length ? undefined : "Aucun propriétaire actif ne fournit ce véhicule à ce lieu."}>
              <Liste value={form.partenaire} onChange={(e) => setForm({ ...form, partenaire: e.target.value })} required
                options={[{ value: "", label: "Choisir" }, ...loueurs.map((p) => ({ value: String(p.id), label: `${p.nom} · ${p.telephone}` }))]} />
            </Champ>
            <div className="grid grid-cols-2 gap-3">
              <Champ label="Véhicule remis" aide="Vide : le véhicule de l'annonce" erreur={erreurs.vehicule}><Saisie value={form.vehicule} onChange={(e) => setForm({ ...form, vehicule: e.target.value })} placeholder="Toyota Corolla grise" /></Champ>
              <Champ label="Immatriculation"><Saisie value={form.immatriculation} onChange={(e) => setForm({ ...form, immatriculation: e.target.value })} placeholder="TG 1234 AB" /></Champ>
            </div>
          </>
        )}
        {attribution && attribution.formule !== "sans_chauffeur" && (
          <Champ label="Chauffeur partenaire" erreur={erreurs.chauffeur}
            aide="6 000 FCFA par jour pour lui, 6 500 au statut Excellence ou s'il a été redemandé ; primes reversées en totalité.">
            <Liste value={form.chauffeur} onChange={(e) => setForm({ ...form, chauffeur: e.target.value })} required
              options={[{ value: "", label: "Choisir" }, ...chauffeurs.map((c) => ({
                value: String(c.id), label: `${c.nom} · ${c.telephone}${c.excellence ? " · Excellence" : ""}${c.demande ? " · redemandé" : ""}`,
              }))]} />
          </Champ>
        )}
      </Panneau>
      <Panneau ouvert={!!retenue} titre="Retenue sur la caution" onFermer={() => setRetenue(null)} onValider={retenir} envoi={envoi} libelle="Enregistrer">
        {retenue && (
          <p className="text-sm bg-light-muted rounded-xl p-3 text-gray-600">
            <strong className="text-dark">{retenue.reference}</strong> · caution de {formatPrice(retenue.caution)}, retour le {dateHeure(retenue.fin)}.
            {" "}Dommage, carburant manquant… signalé par le propriétaire : la retenue lui est versée avec la location, le reste est remboursé au voyageur à la fin du délai de signalement. 0 annule la retenue.
          </p>
        )}
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <Champ label="Montant retenu (FCFA)" erreur={erreurs.montant}>
          <Saisie type="number" min={0} max={retenue?.caution} value={formRetenue.montant} onChange={(e) => setFormRetenue({ ...formRetenue, montant: e.target.value })} required />
        </Champ>
        <Champ label="Motif" aide="Communiqué au voyageur" erreur={erreurs.motif}>
          <Saisie value={formRetenue.motif} maxLength={255} onChange={(e) => setFormRetenue({ ...formRetenue, motif: e.target.value })} placeholder="Rétroviseur cassé (photos du propriétaire)" />
        </Champ>
      </Panneau>
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}
