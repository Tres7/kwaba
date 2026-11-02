"use client";

import { creerChauffeur, modifierChauffeur } from "../api";
import { clesTransferts, useAeroportsAdmin, useChauffeurs } from "../hooks";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useConfigPaiement } from "@/features/paiements";
import AdminTable, { ActionButton, Pill, type Colonne } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Liste, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import { CATEGORIES_TRANSFERT } from "./Aeroports";
import type { ChauffeurAdmin } from "@/types/api/admin";

type Formulaire = Omit<ChauffeurAdmin, "id" | "nb_transferts">;
const VIDE: Formulaire = { prenom: "", nom: "", telephone: "", email: "", aeroports: [], categorie: "berline", vehicule: "", immatriculation: "",
  actif: true, excellence: false, pays_versement: "TG", operateur_versement: "", numero_versement: "" };

export default function Chauffeurs() {
  const queryClient = useQueryClient();
  const { data: config } = useConfigPaiement();
  const { data, isLoading, isError, refetch } = useChauffeurs();
  const { data: aeroports = [] } = useAeroportsAdmin();
  const [edition, setEdition] = useState<ChauffeurAdmin | "nouveau" | null>(null);
  const [form, setForm] = useState<Formulaire>(VIDE);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const pays = config?.pays ?? [];
  const operateurs = pays.find((p) => p.code === form.pays_versement)?.operateurs ?? [];

  const ouvrir = (c: ChauffeurAdmin | "nouveau") => {
    setEdition(c);
    setForm(c === "nouveau" ? VIDE : { ...c });
    setErreurs({});
  };

  const enregistrer = async () => {
    setEnvoi(true);
    try {
      if (edition === "nouveau") await creerChauffeur(form);
      else if (edition) await modifierChauffeur(edition.id, form);
      toast.success("Chauffeur enregistré");
      setEdition(null);
      queryClient.invalidateQueries({ queryKey: clesTransferts.admin });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const nomCategorie = (c: string) => CATEGORIES_TRANSFERT.find((x) => x.code === c)?.nom ?? c;
  const colonnes: Colonne<ChauffeurAdmin>[] = [
    { titre: "Chauffeur", masquerMobile: true, cellule: (c) => <div><p className="font-semibold text-dark">{c.prenom} {c.nom}</p><p className="text-xs text-muted">{c.telephone}</p></div> },
    { titre: "Véhicule", cellule: (c) => <span className="text-xs">{nomCategorie(c.categorie)} · {c.vehicule} · {c.immatriculation}</span> },
    { titre: "Aéroports", cellule: (c) => <span className="text-xs">{c.aeroports.join(", ") || "-"}</span> },
    { titre: "Courses", cellule: (c) => <span className="tabular-nums">{c.nb_transferts}</span> },
    { titre: "Statut", cellule: (c) => <Pill ton={c.actif ? "vert" : "gris"}>{c.actif ? "Actif" : "Désactivé"}</Pill> },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <p className="text-sm text-muted">Chauffeurs partenaires, payés par Mobile Money après chaque course (moins la commission).</p>
        <button onClick={() => ouvrir("nouveau")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouveau chauffeur</button>
      </div>
      <AdminTable colonnes={colonnes} lignes={data} cle={(c) => String(c.id)} titreMobile={(c) => colonnes[0].cellule(c)}
        actions={(c) => <ActionButton onClick={() => ouvrir(c)}>Modifier</ActionButton>}
        chargement={isLoading} erreur={isError} onReessayer={refetch} />

      <Panneau ouvert={!!edition} titre={edition === "nouveau" ? "Nouveau chauffeur" : "Modifier le chauffeur"} onFermer={() => setEdition(null)} onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Prénom" erreur={erreurs.prenom}><Saisie value={form.prenom} onChange={(e) => setForm({ ...form, prenom: e.target.value })} required /></Champ>
          <Champ label="Nom" erreur={erreurs.nom}><Saisie value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} required /></Champ>
          <Champ label="Téléphone" erreur={erreurs.telephone}><Saisie type="tel" value={form.telephone} onChange={(e) => setForm({ ...form, telephone: e.target.value })} required /></Champ>
          <Champ label="Email (facultatif)" erreur={erreurs.email}><Saisie type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Champ>
        </div>
        <fieldset>
          <legend className="block text-xs font-bold text-dark uppercase tracking-wide mb-1.5">Aéroports desservis</legend>
          <div className="flex flex-wrap gap-2">
            {aeroports.map((a) => {
              const actif = form.aeroports.includes(a.code);
              return (
                <button key={a.code} type="button" aria-pressed={actif}
                  onClick={() => setForm({ ...form, aeroports: actif ? form.aeroports.filter((x) => x !== a.code) : [...form.aeroports, a.code] })}
                  className={cn("relative zone-tactile px-3 py-1.5 rounded-full text-sm border", actif ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200")}>
                  {a.ville} ({a.code})
                </button>
              );
            })}
          </div>
          {erreurs.aeroports && <p role="alert" className="text-xs text-red-600 mt-1">{erreurs.aeroports}</p>}
        </fieldset>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Catégorie"><Liste value={form.categorie} onChange={(e) => setForm({ ...form, categorie: e.target.value as Formulaire["categorie"] })}
            options={CATEGORIES_TRANSFERT.map((c) => ({ value: c.code, label: c.nom }))} /></Champ>
          <Champ label="Immatriculation" erreur={erreurs.immatriculation}><Saisie value={form.immatriculation} onChange={(e) => setForm({ ...form, immatriculation: e.target.value })} required /></Champ>
        </div>
        <Champ label="Véhicule (marque, modèle, couleur)" erreur={erreurs.vehicule}><Saisie value={form.vehicule} onChange={(e) => setForm({ ...form, vehicule: e.target.value })} required placeholder="Toyota Corolla grise" /></Champ>
        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Versement Mobile Money</p>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Pays"><Liste value={form.pays_versement} onChange={(e) => setForm({ ...form, pays_versement: e.target.value, operateur_versement: "" })}
            options={pays.map((p) => ({ value: p.code, label: p.nom }))} /></Champ>
          <Champ label="Opérateur" erreur={erreurs.operateur_versement}><Liste value={form.operateur_versement} required
            onChange={(e) => setForm({ ...form, operateur_versement: e.target.value })}
            options={[{ value: "", label: "Choisir" }, ...operateurs.map((o) => ({ value: o.code, label: o.nom }))]} /></Champ>
        </div>
        <Champ label="Numéro (sans l'indicatif)" erreur={erreurs.numero_versement}><Saisie inputMode="numeric" value={form.numero_versement} onChange={(e) => setForm({ ...form, numero_versement: e.target.value })} required /></Champ>
        <Interrupteur label="Actif (reçoit des courses et des missions)" checked={form.actif} onChange={(v) => setForm({ ...form, actif: v })} />
        <Interrupteur label="Chauffeur Excellence (6 500 FCFA par jour au lieu de 6 000)" checked={form.excellence} onChange={(v) => setForm({ ...form, excellence: v })} />
      </Panneau>
    </div>
  );
}
