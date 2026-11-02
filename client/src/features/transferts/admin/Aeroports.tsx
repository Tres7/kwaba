"use client";

import { creerAeroport, enregistrerTarifs, modifierAeroport } from "../api";
import { clesTransferts, useAeroportsAdmin } from "../hooks";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { formatPrice } from "@/lib/utils";
import { Pill } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import type { AeroportAdmin, CategorieTransfert } from "@/types/api/admin";

export const CATEGORIES_TRANSFERT: { code: CategorieTransfert; nom: string }[] = [
  { code: "berline", nom: "Berline" }, { code: "confort", nom: "SUV confort" }, { code: "van", nom: "Minibus" },
];
type Tarifs = Record<CategorieTransfert, { prix: string; actif: boolean }>;
const VIDE = { code: "", nom: "", ville: "", pays: "TG", fuseau: "Africa/Lome", actif: true };

export default function Aeroports() {
  const queryClient = useQueryClient();
  const { data: aeroports, isLoading } = useAeroportsAdmin();
  const [edition, setEdition] = useState<AeroportAdmin | "nouveau" | null>(null);
  const [form, setForm] = useState(VIDE);
  const [tarifs, setTarifs] = useState<Tarifs>({} as Tarifs);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  const ouvrir = (a: AeroportAdmin | "nouveau") => {
    setEdition(a);
    setForm(a === "nouveau" ? VIDE : { code: a.code, nom: a.nom, ville: a.ville, pays: a.pays, fuseau: a.fuseau, actif: a.actif });
    setTarifs(Object.fromEntries(CATEGORIES_TRANSFERT.map(({ code }) => {
      const t = a === "nouveau" ? undefined : a.tarifs.find((x) => x.categorie === code);
      return [code, { prix: t ? String(t.prix) : "", actif: t?.actif ?? !!t }];
    })) as Tarifs);
    setErreurs({});
  };

  const enregistrer = async () => {
    setEnvoi(true);
    setErreurs({});
    try {
      const code = edition === "nouveau" ? (await creerAeroport(form)).code : (edition as AeroportAdmin).code;
      if (edition !== "nouveau") await modifierAeroport(code, form);
      // Only categories with a price have a fare
      const lignes = CATEGORIES_TRANSFERT.filter(({ code: c }) => tarifs[c].prix).map(({ code: c }) => ({ categorie: c, prix: Number(tarifs[c].prix), actif: tarifs[c].actif }));
      await enregistrerTarifs(code, lignes);
      toast.success("Aéroport enregistré");
      setEdition(null);
      queryClient.invalidateQueries({ queryKey: clesTransferts.admin });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <p className="text-sm text-muted">Prix fixes par véhicule, de l&apos;aéroport vers la ville, les mêmes de jour comme de nuit.</p>
        <button onClick={() => ouvrir("nouveau")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouvel aéroport</button>
      </div>
      {isLoading ? <div className="h-40 skeleton rounded-2xl" /> : (
        <ul className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {aeroports?.map((a) => (
            <li key={a.code}>
              <button type="button" onClick={() => ouvrir(a)} className="w-full text-left bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-card transition-shadow">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-heading font-bold text-dark">{a.ville} <span className="text-muted font-mono text-sm">{a.code}</span></p>
                  <Pill ton={a.actif ? "vert" : "gris"}>{a.actif ? "Proposé" : "Désactivé"}</Pill>
                </div>
                <p className="text-xs text-muted mt-0.5 truncate">{a.nom}</p>
                <ul className="mt-3 space-y-1 text-sm">
                  {CATEGORIES_TRANSFERT.map(({ code, nom }) => {
                    const t = a.tarifs.find((x) => x.categorie === code);
                    return (
                      <li key={code} className="flex justify-between gap-2">
                        <span className="text-gray-600">{nom}</span>
                        <span className={t?.actif ? "text-dark tabular-nums" : "text-gray-400 tabular-nums"}>{t ? formatPrice(t.prix) : "-"}{t && !t.actif ? " (désactivé)" : ""}</span>
                      </li>
                    );
                  })}
                </ul>
              </button>
            </li>
          ))}
        </ul>
      )}

      <Panneau ouvert={!!edition} titre={edition === "nouveau" ? "Nouvel aéroport" : "Modifier l'aéroport"} onFermer={() => setEdition(null)} onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <div className="grid grid-cols-3 gap-3">
          <Champ label="Code IATA" erreur={erreurs.code}>
            <Saisie value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} maxLength={3} required disabled={edition !== "nouveau"} placeholder="LFW" />
          </Champ>
          <Champ label="Ville" erreur={erreurs.ville} className="col-span-2"><Saisie value={form.ville} onChange={(e) => setForm({ ...form, ville: e.target.value })} required /></Champ>
        </div>
        <Champ label="Nom de l'aéroport" erreur={erreurs.nom}><Saisie value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} required /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Pays (code)" erreur={erreurs.pays}><Saisie value={form.pays} onChange={(e) => setForm({ ...form, pays: e.target.value.toUpperCase() })} maxLength={2} required /></Champ>
          <Champ label="Fuseau horaire" erreur={erreurs.fuseau}><Saisie value={form.fuseau} onChange={(e) => setForm({ ...form, fuseau: e.target.value })} required placeholder="Africa/Lome" /></Champ>
        </div>
        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Tarifs (FCFA, hors nuit)</p>
        {CATEGORIES_TRANSFERT.map(({ code, nom }) => (
          <div key={code} className="grid grid-cols-[1fr_140px_auto] items-center gap-3">
            <span className="text-sm font-semibold text-dark">{nom}</span>
            <Saisie type="number" min={0} inputMode="numeric" aria-label={`Prix ${nom}`} value={tarifs[code]?.prix ?? ""} placeholder="Non proposé"
              onChange={(e) => setTarifs({ ...tarifs, [code]: { ...tarifs[code], prix: e.target.value, actif: tarifs[code]?.actif || !!e.target.value } })} />
            <label className="flex items-center gap-1.5 text-xs text-gray-600">
              <input type="checkbox" className="accent-primary w-4 h-4" checked={!!tarifs[code]?.actif} disabled={!tarifs[code]?.prix}
                onChange={(e) => setTarifs({ ...tarifs, [code]: { ...tarifs[code], actif: e.target.checked } })} /> Actif
            </label>
          </div>
        ))}
        <Interrupteur label="Aéroport proposé aux voyageurs" checked={form.actif} onChange={(v) => setForm({ ...form, actif: v })} />
      </Panneau>
    </div>
  );
}
