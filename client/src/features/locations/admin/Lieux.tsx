"use client";

import { creerLieu, modifierLieu } from "../api";
import { clesLocations, useLieuxAdmin } from "../hooks";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { formatPrice } from "@/lib/utils";
import AdminTable, { ActionButton, Pill, type Colonne } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Liste, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import type { LieuRemise } from "@/types/api/admin";

const FUSEAUX = [
  { value: "Africa/Lome", label: "Togo, Ghana, Côte d'Ivoire, Sénégal… (UTC)" },
  { value: "Africa/Porto-Novo", label: "Bénin, Niger, Nigeria (UTC+1)" },
];
const VIDE = { nom: "", ville: "", fuseau: "Africa/Lome" as LieuRemise["fuseau"], adresse_requise: false, frais: "0", actif: true, ordre: "0" };

export default function Lieux() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useLieuxAdmin();
  const [edition, setEdition] = useState<LieuRemise | "nouveau" | null>(null);
  const [form, setForm] = useState(VIDE);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const ouvrir = (l: LieuRemise | "nouveau") => {
    setEdition(l);
    setForm(l === "nouveau" ? VIDE : { ...l, frais: String(l.frais), ordre: String(l.ordre) });
    setErreurs({});
  };

  const enregistrer = async () => {
    setEnvoi(true);
    const corps = { ...form, frais: Number(form.frais) || 0, ordre: Number(form.ordre) || 0 };
    try {
      if (edition === "nouveau") await creerLieu(corps);
      else if (edition) await modifierLieu(edition.id, corps);
      toast.success("Lieu enregistré");
      setEdition(null);
      queryClient.invalidateQueries({ queryKey: clesLocations.admin });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const colonnes: Colonne<LieuRemise>[] = [
    { titre: "Lieu", masquerMobile: true, cellule: (l) => <div><p className="font-semibold text-dark">{l.nom}</p><p className="text-xs text-muted">{l.ville}</p></div> },
    { titre: "Adresse du voyageur", cellule: (l) => (l.adresse_requise ? "Oui (livraison)" : "Non") },
    { titre: "Frais", cellule: (l) => <span className="tabular-nums">{l.frais ? formatPrice(l.frais) : "Aucun"}</span> },
    { titre: "Statut", cellule: (l) => <Pill ton={l.actif ? "vert" : "gris"}>{l.actif ? "Proposé" : "Désactivé"}</Pill> },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <p className="text-sm text-muted">Où les loueurs remettent et récupèrent les véhicules.</p>
        <button onClick={() => ouvrir("nouveau")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouveau lieu</button>
      </div>
      <AdminTable colonnes={colonnes} lignes={data} cle={(l) => String(l.id)} titreMobile={(l) => colonnes[0].cellule(l)}
        actions={(l) => <ActionButton onClick={() => ouvrir(l)}>Modifier</ActionButton>}
        chargement={isLoading} erreur={isError} onReessayer={refetch} />

      <Panneau ouvert={!!edition} titre={edition === "nouveau" ? "Nouveau lieu de remise" : "Modifier le lieu"} onFermer={() => setEdition(null)} onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <Champ label="Nom" erreur={erreurs.nom} aide="Par ex. « Aéroport de Lomé » ou « Livraison à votre adresse, Lomé »">
          <Saisie value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} required maxLength={120} />
        </Champ>
        <Champ label="Ville" erreur={erreurs.ville}><Saisie value={form.ville} onChange={(e) => setForm({ ...form, ville: e.target.value })} required /></Champ>
        <Champ label="Fuseau horaire"><Liste value={form.fuseau} onChange={(e) => setForm({ ...form, fuseau: e.target.value as LieuRemise["fuseau"] })} options={FUSEAUX} /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Frais (FCFA)" aide="Ajoutés à la remise et au retour"><Saisie type="number" min={0} value={form.frais} onChange={(e) => setForm({ ...form, frais: e.target.value })} /></Champ>
          <Champ label="Ordre d'affichage"><Saisie type="number" min={0} value={form.ordre} onChange={(e) => setForm({ ...form, ordre: e.target.value })} /></Champ>
        </div>
        <Interrupteur label="Le voyageur indique son adresse (livraison)" checked={form.adresse_requise} onChange={(v) => setForm({ ...form, adresse_requise: v })} />
        <Interrupteur label="Proposé aux voyageurs" checked={form.actif} onChange={(v) => setForm({ ...form, actif: v })} />
      </Panneau>
    </div>
  );
}
