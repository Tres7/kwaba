"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, FileSignature } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "@/lib/utils";
import Panneau, { Champ, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import type { ModeleContrat } from "@/types/api/admin";
import { enregistrerModele, listerModeles } from "../api";

/** Contract templates, versioned: contracts already issued keep the text of their version. */
export default function ModelesContrats() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "contrats-modeles"],
    queryFn: () => listerModeles<ModeleContrat>(),
  });
  const [edition, setEdition] = useState<ModeleContrat | null>(null);
  const [titre, setTitre] = useState("");
  const [corps, setCorps] = useState("");
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const zone = useRef<HTMLTextAreaElement>(null);

  const ouvrir = (m: ModeleContrat) => { setEdition(m); setTitre(m.titre); setCorps(m.corps); setErreurs({}); };

  // Inserts the variable at the cursor position
  const inserer = (cle: string) => {
    const z = zone.current;
    const texte = `{{ ${cle} }}`;
    if (!z) return setCorps((c) => c + texte);
    const debut = z.selectionStart, fin = z.selectionEnd;
    setCorps((c) => c.slice(0, debut) + texte + c.slice(fin));
    requestAnimationFrame(() => { z.focus(); z.setSelectionRange(debut + texte.length, debut + texte.length); });
  };

  const enregistrer = async () => {
    if (!edition) return;
    setEnvoi(true);
    setErreurs({});
    try {
      const m = await enregistrerModele<ModeleContrat>(edition.type, { titre, corps });
      toast.success(m.version > edition.version ? `Modèle enregistré (version ${m.version})` : "Aucune modification");
      setEdition(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "contrats-modeles"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-4">
      <div role="note" className="flex gap-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl px-4 py-3 text-sm">
        <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" aria-hidden />
        <p>Ces textes sont des projets de rédaction : faites-les relire par un juriste avant d&apos;envoyer les premiers contrats. Chaque modification crée une nouvelle version ; les contrats déjà émis gardent leur texte.</p>
      </div>
      {isLoading ? <div className="h-40 skeleton rounded-2xl" /> : (
        <ul className="grid sm:grid-cols-2 gap-3">
          {data?.modeles.map((m) => (
            <li key={m.type} className="bg-white rounded-2xl border border-gray-100 p-4 flex gap-3">
              <span className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><FileSignature size={18} aria-hidden /></span>
              <div className="flex-1 min-w-0">
                <p className="font-heading font-bold text-dark">{m.type_libelle}</p>
                <p className="text-sm text-dark truncate">{m.titre}</p>
                <p className="text-xs text-muted mt-0.5">Version {m.version} · modifié le {formatDate(m.modifie_le)}</p>
                <button type="button" onClick={() => ouvrir(m)} className="mt-3 px-3 py-1.5 rounded-lg text-xs font-semibold border border-gray-200 text-dark hover:bg-gray-50">Modifier le texte</button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Panneau ouvert={!!edition} titre={`Modèle : ${edition?.type_libelle ?? ""}`} onFermer={() => setEdition(null)} onValider={enregistrer} envoi={envoi}>
        <Champ label="Titre" erreur={erreurs.titre}>
          <Saisie value={titre} onChange={(e) => setTitre(e.target.value)} required />
        </Champ>
        <Champ label="Texte du contrat" erreur={erreurs.corps} aide="Un paragraphe qui commence par « ## » devient un titre d'article. Séparez les paragraphes par une ligne vide.">
          <Zone ref={zone} rows={18} value={corps} onChange={(e) => setCorps(e.target.value)} className="font-mono text-xs leading-relaxed" />
        </Champ>
        <div>
          <p className="text-xs font-bold text-dark uppercase tracking-wide mb-1.5">Variables (cliquez pour insérer)</p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(data?.variables ?? {}).map(([cle, libelle]) => (
              <button key={cle} type="button" onClick={() => inserer(cle)} title={libelle}
                className="px-2 py-1 rounded-lg bg-gray-50 border border-gray-200 text-[11px] font-mono text-dark hover:border-primary hover:text-primary">
                {cle}
              </button>
            ))}
          </div>
        </div>
        {erreurs.detail && <p role="alert" className="text-sm text-red-600">{erreurs.detail}</p>}
      </Panneau>
    </div>
  );
}
