"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import { Champ, Interrupteur, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import { Pill } from "@/components/backoffice/AdminTable";
import type { SocieteAdmin } from "@/types/api/admin";

type Form = Omit<SocieteAdmin, "complets" | "signature_presente">;
type ChampTexte = Exclude<keyof Form, "assujetti_tva">;
// The API client sends JSON by default: header needed to send the scanned signature
const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

export function useSociete() {
  return useQuery({
    queryKey: ["admin", "documents", "societe"],
    queryFn: async () => (await api.get<SocieteAdmin>("/v1/admin/documents/societe/")).data,
  });
}

/** Legal information printed at the top of vouchers, receipts and invoices. */
export default function Societe() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useSociete();
  const [form, setForm] = useState<Form | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const [signature, setSignature] = useState<File | null>(null);
  const [supprimer, setSupprimer] = useState(false);
  const apercuSignature = useApercuSignature(data?.signature_presente, signature);

  useEffect(() => { if (data) setForm(data); }, [data]);

  if (isLoading || !form) return <div className="h-96 skeleton rounded-2xl" />;

  const champ = <K extends keyof Form>(k: K) => (v: Form[K]) => setForm((f) => (f ? { ...f, [k]: v } : f));
  const texte = (k: ChampTexte, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <Champ label={label} erreur={erreurs[k]}>
      <Saisie value={form[k]} onChange={(e) => champ(k)(e.target.value)} {...props} />
    </Champ>
  );

  const enregistrer = async () => {
    setEnvoi(true);
    setErreurs({});
    try {
      const corps = new FormData();
      for (const [k, v] of Object.entries(form ?? {})) {
        if (k === "complets" || k === "signature_presente") continue;  // computed by the server
        corps.append(k, typeof v === "boolean" ? (v ? "true" : "false") : String(v ?? ""));
      }
      if (signature) corps.append("signature_representant", signature);
      else if (supprimer) corps.append("supprimer_signature", "true");
      const { data: maj } = await api.put<SocieteAdmin>("/v1/admin/documents/societe/", corps, MULTIPART);
      queryClient.setQueryData(["admin", "documents", "societe"], maj);
      queryClient.invalidateQueries({ queryKey: ["admin", "documents", "signature"] });
      setSignature(null);
      setSupprimer(false);
      toast.success("Informations enregistrées");
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <form method="post" onSubmit={(e) => { e.preventDefault(); if (!envoi) enregistrer(); }}
      className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6 space-y-5 max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted flex-1 min-w-[220px]">
          Ces informations apparaissent en tête de chaque document. La raison sociale et l&apos;adresse sont obligatoires pour émettre une facture.
        </p>
        <Pill ton={data?.complets ? "vert" : "orange"}>{data?.complets ? "Complètes" : "À compléter"}</Pill>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {texte("raison_sociale", "Raison sociale", { required: true, placeholder: "Ex. Kwa-Ba SARL" })}
        {texte("nom_commercial", "Nom commercial")}
        {texte("forme_juridique", "Forme juridique", { placeholder: "SARL, SAS, SA…" })}
        {texte("pays", "Pays")}
        <Champ label="Adresse du siège" erreur={erreurs.adresse} className="sm:col-span-2">
          <Zone rows={2} value={form.adresse} onChange={(e) => champ("adresse")(e.target.value)} required />
        </Champ>
        {texte("nif", "NIF", { placeholder: "Numéro d'identification fiscale" })}
        {texte("rccm", "RCCM", { placeholder: "Ex. TG-LOM-01-2026-B12-00001" })}
        {texte("telephone", "Téléphone", { type: "tel" })}
        {texte("email", "Email", { type: "email" })}
        {texte("site", "Site web")}
      </div>

      <fieldset className="border-t border-gray-100 pt-4 space-y-4">
        {/* float: the legend sits in the flow, below the border, like a section title */}
        <legend className="float-left w-full text-sm font-semibold text-dark">Signataire des contrats</legend>
        <div className="clear-both grid sm:grid-cols-2 gap-4">
          {texte("representant_nom", "Représentant légal", { placeholder: "Prénom et nom" })}
          {texte("representant_qualite", "Qualité", { placeholder: "Cogérant, gérant…" })}
        </div>
        <Champ label="Signature scannée" erreur={erreurs.signature_representant}
          aide="Imprimée sur les contrats, côté Kwa-Ba. Signature à l'encre foncée sur papier blanc : le fond devient transparent.">
          <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => { setSignature(e.target.files?.[0] ?? null); setSupprimer(false); }}
            className="block w-full text-sm text-dark file:mr-3 file:px-4 file:py-2 file:rounded-xl file:border-0 file:bg-primary/10 file:text-primary file:font-semibold" />
        </Champ>
        {apercuSignature && !supprimer && (
          <div className="flex items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={apercuSignature} alt="Signature du représentant" className="h-16 max-w-[240px] object-contain rounded-lg border border-gray-100 bg-white p-1" />
            {data?.signature_presente && !signature && (
              <button type="button" onClick={() => setSupprimer(true)} className="text-sm font-semibold text-red-700 hover:underline">Retirer</button>
            )}
          </div>
        )}
        {supprimer && <p className="text-sm text-muted">La signature sera retirée à l&apos;enregistrement.</p>}
      </fieldset>

      <div className="border-t border-gray-100 pt-4 space-y-3">
        <Interrupteur label="Assujettie à la TVA" checked={form.assujetti_tva} onChange={champ("assujetti_tva")} />
        {form.assujetti_tva && (
          <Champ label="Taux de TVA (%)" erreur={erreurs.taux_tva} aide="Les prix du site sont TTC : la TVA est extraite du total." className="sm:w-64">
            <Saisie type="number" min={0} max={100} step="0.01" value={form.taux_tva} onChange={(e) => champ("taux_tva")(e.target.value)} />
          </Champ>
        )}
        <Champ label="Mentions en pied de page" erreur={erreurs.mentions} aide="Capital social, conditions de paiement, coordonnées bancaires…">
          <Zone rows={3} value={form.mentions} onChange={(e) => champ("mentions")(e.target.value)} />
        </Champ>
      </div>

      {erreurs.detail && <p role="alert" className="text-sm text-red-600">{erreurs.detail}</p>}
      <div className="flex justify-end">
        <button type="submit" disabled={envoi} className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary-600 disabled:opacity-50">
          {envoi ? "Enregistrement…" : "Enregistrer"}
        </button>
      </div>
    </form>
  );
}

/** Preview: the chosen file, otherwise the saved signature (read through the API, never a public URL). */
function useApercuSignature(presente: boolean | undefined, fichier: File | null): string | null {
  const { data: enregistree } = useQuery({
    queryKey: ["admin", "documents", "signature"],
    queryFn: async () => URL.createObjectURL((await api.get<Blob>("/v1/admin/documents/societe/signature/", { responseType: "blob" })).data),
    enabled: !!presente,
  });
  const [locale, setLocale] = useState<string | null>(null);
  useEffect(() => {
    if (!fichier) return setLocale(null);
    const url = URL.createObjectURL(fichier);
    setLocale(url);
    return () => URL.revokeObjectURL(url);
  }, [fichier]);
  return locale ?? (presente ? enregistree ?? null : null);
}
