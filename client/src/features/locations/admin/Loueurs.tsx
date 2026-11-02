"use client";

import { creerLoueur, modifierLoueur } from "../api";
import { clesLocations, useCategoriesAdmin, useLieuxAdmin, useLoueursAdmin } from "../hooks";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { cn, formatDate } from "@/lib/utils";
import { useConfigPaiement } from "@/features/paiements";
import AdminTable, { ActionButton, Pill, type Colonne } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Liste, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import type { Loueur } from "@/types/api/admin";

type Formulaire = Omit<Loueur, "id" | "nb_locations" | "nb_vehicules" | "commission_pourcent" | "fondateur_debut" | "fondateur_fin"> & {
  fondateur_debut: string; fondateur_fin: string;
};
const VIDE: Formulaire = { nom: "", contact: "", telephone: "", email: "", categories: [], lieux: [], actif: true,
  fondateur_debut: "", fondateur_fin: "", pays_versement: "TG", operateur_versement: "", numero_versement: "" };

/** Checkboxes as chips (categories, places). */
function Choix<T extends { id: number; nom: string }>({ label, elements, valeur, onChange, erreur }: {
  label: string; elements: T[]; valeur: number[]; onChange: (v: number[]) => void; erreur?: string;
}) {
  return (
    <fieldset>
      <legend className="block text-xs font-bold text-dark uppercase tracking-wide mb-1.5">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {elements.map((e) => {
          const actif = valeur.includes(e.id);
          return (
            <button key={e.id} type="button" aria-pressed={actif} onClick={() => onChange(actif ? valeur.filter((x) => x !== e.id) : [...valeur, e.id])}
              className={cn("relative zone-tactile px-3 py-1.5 rounded-full text-sm border", actif ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200")}>
              {e.nom}
            </button>
          );
        })}
      </div>
      {erreur && <p role="alert" className="text-xs text-red-600 mt-1">{erreur}</p>}
    </fieldset>
  );
}

/** Partner vehicle owners (individuals or agencies), paid after each rental minus the commission. */
export default function Loueurs() {
  const queryClient = useQueryClient();
  const { data: config } = useConfigPaiement();
  const { data, isLoading, isError, refetch } = useLoueursAdmin();
  const { data: categories = [] } = useCategoriesAdmin();
  const { data: lieux = [] } = useLieuxAdmin();
  const [edition, setEdition] = useState<Loueur | "nouveau" | null>(null);
  const [form, setForm] = useState<Formulaire>(VIDE);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const pays = config?.pays ?? [];
  const operateurs = pays.find((p) => p.code === form.pays_versement)?.operateurs ?? [];

  const ouvrir = (l: Loueur | "nouveau") => {
    setEdition(l);
    setForm(l === "nouveau" ? { ...VIDE, operateur_versement: "" }
      : { ...l, fondateur_debut: l.fondateur_debut ?? "", fondateur_fin: l.fondateur_fin ?? "" });
    setErreurs({});
  };

  const enregistrer = async () => {
    setEnvoi(true);
    const corps = { ...form, fondateur_debut: form.fondateur_debut || null, fondateur_fin: form.fondateur_fin || null };
    try {
      if (edition === "nouveau") await creerLoueur(corps);
      else if (edition) await modifierLoueur(edition.id, corps);
      toast.success("Propriétaire enregistré");
      setEdition(null);
      queryClient.invalidateQueries({ queryKey: clesLocations.admin });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const nomsDe = <T extends { id: number; nom: string }>(ids: number[], liste: T[]) => liste.filter((x) => ids.includes(x.id)).map((x) => x.nom).join(", ") || "-";
  const colonnes: Colonne<Loueur>[] = [
    { titre: "Propriétaire", masquerMobile: true, cellule: (l) => <div><p className="font-semibold text-dark">{l.nom}</p><p className="text-xs text-muted">{l.contact} · {l.telephone}</p></div> },
    { titre: "Véhicules", cellule: (l) => <span className="tabular-nums">{l.nb_vehicules}</span> },
    { titre: "Commission", cellule: (l) => <span className="text-xs whitespace-nowrap">{l.commission_pourcent ?? "-"} %{l.fondateur_fin ? ` · fondateur jusqu'au ${formatDate(l.fondateur_fin)}` : ""}</span> },
    { titre: "Lieux", cellule: (l) => <span className="text-xs">{nomsDe(l.lieux, lieux)}</span> },
    { titre: "Locations", cellule: (l) => <span className="tabular-nums">{l.nb_locations}</span> },
    { titre: "Statut", cellule: (l) => <Pill ton={l.actif ? "vert" : "gris"}>{l.actif ? "Actif" : "Désactivé"}</Pill> },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <p className="text-sm text-muted">
          Propriétaires (particuliers ou agences), payés par Mobile Money après chaque location, moins la commission : 15 %, 10 %
          pendant le Programme Fondateurs (20 premiers, 6 mois), 12 % après 20 locations sans incident.
        </p>
        <button onClick={() => ouvrir("nouveau")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouveau propriétaire</button>
      </div>
      <AdminTable colonnes={colonnes} lignes={data} cle={(l) => String(l.id)} titreMobile={(l) => colonnes[0].cellule(l)}
        actions={(l) => <ActionButton onClick={() => ouvrir(l)}>Modifier</ActionButton>}
        chargement={isLoading} erreur={isError} onReessayer={refetch} />

      <Panneau ouvert={!!edition} titre={edition === "nouveau" ? "Nouveau propriétaire" : "Modifier le propriétaire"} onFermer={() => setEdition(null)} onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <Champ label="Nom du propriétaire ou de l'agence" erreur={erreurs.nom}><Saisie value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} required /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Contact" erreur={erreurs.contact}><Saisie value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} required /></Champ>
          <Champ label="Téléphone" erreur={erreurs.telephone}><Saisie type="tel" value={form.telephone} onChange={(e) => setForm({ ...form, telephone: e.target.value })} required placeholder="+228 90 00 00 00" /></Champ>
        </div>
        <Champ label="Email (facultatif)" aide="Reçoit le détail des locations attribuées" erreur={erreurs.email}>
          <Saisie type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Champ>
        {form.categories.length > 0 && (
          <Choix label="Ancien catalogue (véhicules sans propriétaire)" elements={categories.filter((c) => !c.proprietaire)} valeur={form.categories}
            onChange={(v) => setForm({ ...form, categories: v })} erreur={erreurs.categories} />
        )}
        <Choix label="Lieux de remise" elements={lieux} valeur={form.lieux} onChange={(v) => setForm({ ...form, lieux: v })} erreur={erreurs.lieux} />
        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Programme Fondateurs (10 % pendant 6 mois)</p>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Début"><Saisie type="date" value={form.fondateur_debut} onChange={(e) => setForm({ ...form, fondateur_debut: e.target.value })} /></Champ>
          <Champ label="Fin" erreur={erreurs.fondateur_fin}><Saisie type="date" value={form.fondateur_fin} onChange={(e) => setForm({ ...form, fondateur_fin: e.target.value })} /></Champ>
        </div>
        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Versement Mobile Money</p>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Pays"><Liste value={form.pays_versement} onChange={(e) => setForm({ ...form, pays_versement: e.target.value, operateur_versement: "" })}
            options={pays.map((p) => ({ value: p.code, label: p.nom }))} /></Champ>
          <Champ label="Opérateur" erreur={erreurs.operateur_versement}><Liste value={form.operateur_versement} required
            onChange={(e) => setForm({ ...form, operateur_versement: e.target.value })}
            options={[{ value: "", label: "Choisir" }, ...operateurs.map((o) => ({ value: o.code, label: o.nom }))]} /></Champ>
        </div>
        <Champ label="Numéro (sans l'indicatif)" erreur={erreurs.numero_versement}><Saisie inputMode="numeric" value={form.numero_versement} onChange={(e) => setForm({ ...form, numero_versement: e.target.value })} required /></Champ>
        <Interrupteur label="Actif (reçoit des locations)" checked={form.actif} onChange={(v) => setForm({ ...form, actif: v })} />
      </Panneau>
    </div>
  );
}
