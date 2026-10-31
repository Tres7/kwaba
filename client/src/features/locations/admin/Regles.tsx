"use client";

import { enregistrerRegles, lireRegles } from "../api";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Champ, Interrupteur, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";

const VIDE = {
  commission_pourcent: "15", delai_min_jours: "2", duree_max_jours: "30", annulation_gratuite_heures: "48", conditions: "",
  caution_en_ligne: true, restitution_caution_heures: "24",
};

/** Rental rules: as long as they are not saved, rental is not offered on the site. */
export default function Regles() {
  const queryClient = useQueryClient();
  const { data: regles, isLoading } = useQuery({
    queryKey: ["admin", "location", "regles"],
    queryFn: lireRegles,
  });
  const [form, setForm] = useState(VIDE);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (regles) setForm({ ...regles, delai_min_jours: String(regles.delai_min_jours), duree_max_jours: String(regles.duree_max_jours),
      annulation_gratuite_heures: String(regles.annulation_gratuite_heures), restitution_caution_heures: String(regles.restitution_caution_heures) });
  }, [regles]);

  const enregistrer = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    try {
      await enregistrerRegles(form);
      toast.success("Règles enregistrées");
      queryClient.invalidateQueries({ queryKey: ["admin", "location", "regles"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  if (isLoading) return <div className="h-64 skeleton rounded-2xl" />;
  return (
    <form method="post" onSubmit={enregistrer} className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6 space-y-4 max-w-2xl">
      {!regles && <p className="text-sm bg-amber-50 text-amber-900 rounded-xl p-3">La location n&apos;est pas encore proposée sur le site : enregistrez ces règles pour l&apos;ouvrir.</p>}
      {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
      <div className="grid sm:grid-cols-2 gap-4">
        <Champ label="Commission sur le véhicule (%)" aide="Payée par le propriétaire (15 %) ; 10 % pour un fondateur, 12 % après 20 locations sans incident" erreur={erreurs.commission_pourcent}>
          <Saisie type="number" min={0} max={100} step="0.5" value={form.commission_pourcent} onChange={(e) => setForm({ ...form, commission_pourcent: e.target.value })} required />
        </Champ>
        <Champ label="Réservation au plus tard (jours avant)" aide="Temps de préparation du propriétaire et du chauffeur" erreur={erreurs.delai_min_jours}>
          <Saisie type="number" min={1} value={form.delai_min_jours} onChange={(e) => setForm({ ...form, delai_min_jours: e.target.value })} required />
        </Champ>
        <Champ label="Durée maximale (jours)" erreur={erreurs.duree_max_jours}>
          <Saisie type="number" min={1} value={form.duree_max_jours} onChange={(e) => setForm({ ...form, duree_max_jours: e.target.value })} required />
        </Champ>
        <Champ label="Annulation gratuite (heures avant)" aide="Intégral au-delà (48) ; 50 % jusqu'à 24 h avant ; rien ensuite" erreur={erreurs.annulation_gratuite_heures}>
          <Saisie type="number" min={0} value={form.annulation_gratuite_heures} onChange={(e) => setForm({ ...form, annulation_gratuite_heures: e.target.value })} required />
        </Champ>
      </div>
      <div className="rounded-xl border border-gray-100 p-4 space-y-3">
        <Interrupteur label="Caution payée en ligne et gardée par Kwa-Ba" checked={form.caution_en_ligne}
          onChange={(v) => setForm({ ...form, caution_en_ligne: v })} />
        <p className="text-xs text-muted">
          {form.caution_en_ligne
            ? "Le voyageur paie la caution avec la location et ne règle rien au propriétaire. Après le retour, le propriétaire signale les dommages à Kwa-Ba ; la retenue (Suivi des locations) lui est versée, le reste est remboursé au voyageur."
            : "Le voyageur règle la caution au propriétaire à la remise du véhicule : Kwa-Ba n'en a pas le contrôle."}
        </p>
        {form.caution_en_ligne && (
          <Champ label="Signalement des dommages (heures après le retour)" aide="Ensuite, la caution moins la retenue est remboursée au voyageur et le propriétaire payé"
            erreur={erreurs.restitution_caution_heures}>
            <Saisie type="number" min={1} value={form.restitution_caution_heures} onChange={(e) => setForm({ ...form, restitution_caution_heures: e.target.value })} required />
          </Champ>
        )}
      </div>
      <Champ label="Conditions affichées au voyageur" aide="Âge minimum, permis, carburant, kilométrage…" erreur={erreurs.conditions}>
        <Zone rows={4} value={form.conditions} onChange={(e) => setForm({ ...form, conditions: e.target.value })} />
      </Champ>
      <div className="flex justify-end">
        <button type="submit" disabled={envoi} className="px-6 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-50">{envoi ? "Enregistrement…" : "Enregistrer"}</button>
      </div>
    </form>
  );
}
