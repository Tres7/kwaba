"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import { isoDate } from "@/lib/utils";
import Panneau, { Champ, Liste, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import type { AdminUser, ConditionsHote as Conditions } from "@/types/api/admin";

const CATEGORIES = [
  { value: "particulier", label: "Hôte particulier (8 %)" },
  { value: "hotel", label: "Hôtel ou résidence hôtelière (12 %)" },
];

/** A host's commission (grid of 18 October 2026): category and Founders Programme (5 % for 6 months, 50 hosts). */
export default function ConditionsHote({ hote, onFermer }: { hote: AdminUser | null; onFermer: () => void }) {
  const queryClient = useQueryClient();
  const actuelles = hote?.conditions;
  const [form, setForm] = useState({
    categorie: actuelles?.categorie ?? "particulier",
    fondateur_debut: actuelles?.fondateur_debut ?? "",
    fondateur_fin: actuelles?.fondateur_fin ?? "",
  });
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const sixMois = () => {
    const debut = new Date();
    const fin = new Date(debut);
    fin.setMonth(fin.getMonth() + 6);
    setForm({ ...form, categorie: "particulier", fondateur_debut: isoDate(debut), fondateur_fin: isoDate(fin) });
  };

  const valider = async () => {
    if (!hote) return;
    setEnvoi(true);
    setErreurs({});
    try {
      const conditions: Partial<Conditions> = {
        categorie: form.categorie as Conditions["categorie"],
        fondateur_debut: form.fondateur_debut || null,
        fondateur_fin: form.fondateur_fin || null,
      };
      await api.patch(`/v1/admin/users/${hote.id}/`, { conditions });
      toast.success("Commission mise à jour");
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      onFermer();
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const nom = hote ? `${hote.first_name} ${hote.last_name}`.trim() || hote.email : "";
  return (
    <Panneau ouvert={!!hote} titre={`Commission de ${nom}`} onFermer={onFermer} onValider={valider} envoi={envoi}>
      <p className="text-sm text-gray-600">
        Taux appliqué aujourd&apos;hui : <strong>{actuelles?.commission_pourcent ?? 8} %</strong>. Il est figé sur chaque réservation au moment
        où elle est faite, et repris dans le contrat de l&apos;hôte (contrat hôtel pour un hôtel).
      </p>
      {(erreurs.conditions || erreurs.detail) && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.conditions || erreurs.detail}</p>}
      <Champ label="Catégorie">
        <Liste options={CATEGORIES} value={form.categorie} onChange={(e) => setForm({ ...form, categorie: e.target.value as Conditions["categorie"] })} />
      </Champ>
      {form.categorie === "particulier" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-bold text-dark uppercase tracking-wide">Programme Fondateurs (5 %)</p>
            <button type="button" onClick={sixMois} className="text-xs font-semibold text-primary hover:underline">6 mois à partir d&apos;aujourd&apos;hui</button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Champ label="Début"><Saisie type="date" value={form.fondateur_debut} onChange={(e) => setForm({ ...form, fondateur_debut: e.target.value })} /></Champ>
            <Champ label="Fin"><Saisie type="date" value={form.fondateur_fin} onChange={(e) => setForm({ ...form, fondateur_fin: e.target.value })} /></Champ>
          </div>
          <p className="text-xs text-gray-500">Réservé aux 50 premiers hôtes. Laissez vide si l&apos;hôte n&apos;en bénéficie pas.</p>
        </div>
      )}
    </Panneau>
  );
}
