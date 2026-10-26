"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { messageErreurPdf, telechargerFacture } from "@/lib/documents";
import { formatDate, formatPrice } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import { useSociete } from "@/components/backoffice/documents/Societe";
import type { FactureAdmin } from "@/types/api/admin";

type Ligne = { libelle: string; quantite: string; prix_unitaire: string };
const LIGNE_VIDE: Ligne = { libelle: "", quantite: "1", prix_unitaire: "" };
const CLIENT_VIDE = { client_nom: "", client_email: "", client_adresse: "" };

/** Issued invoices, and issuing of a free-form invoice (service outside a booking). */
export default function Factures() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const { data: societe } = useSociete();
  const [q, setQ] = useState("");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<FactureAdmin>("documents/factures", { q: recherche });

  const [ouvert, setOuvert] = useState(false);
  const [client, setClient] = useState(CLIENT_VIDE);
  const [lignes, setLignes] = useState<Ligne[]>([LIGNE_VIDE]);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const [telechargement, setTelechargement] = useState<string | null>(null);

  const total = lignes.reduce((s, l) => s + (Number(l.quantite) || 0) * (Number(l.prix_unitaire) || 0), 0);
  const ligne = (i: number, k: keyof Ligne, v: string) => setLignes((ls) => ls.map((l, j) => (j === i ? { ...l, [k]: v } : l)));
  const ouvrir = () => { setClient(CLIENT_VIDE); setLignes([LIGNE_VIDE]); setErreurs({}); setOuvert(true); };

  const telecharger = async (f: FactureAdmin) => {
    setTelechargement(f.id);
    try {
      await telechargerFacture(f);
    } catch (err) {
      toast.error(await messageErreurPdf(err));
    } finally {
      setTelechargement(null);
    }
  };

  const emettre = async () => {
    setEnvoi(true);
    setErreurs({});
    try {
      const { data: f } = await api.post<FactureAdmin>("/v1/admin/documents/factures/", {
        ...client,
        lignes: lignes.map((l) => ({ libelle: l.libelle, quantite: Number(l.quantite) || 0, prix_unitaire: Number(l.prix_unitaire) || 0 })),
      });
      toast.success(`Facture ${f.numero} émise`);
      setOuvert(false);
      queryClient.invalidateQueries({ queryKey: ["admin", "documents/factures"] });
      await telecharger(f);
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const colonnes: Colonne<FactureAdmin>[] = [
    { titre: "Facture", masquerMobile: true, cellule: (f) => <div><p className="font-semibold text-dark font-mono">{f.numero}</p><p className="text-xs text-muted">{formatDate(f.emise_le)}</p></div> },
    { titre: "Client", cellule: (f) => <div className="text-xs min-w-0"><p className="text-dark font-medium truncate">{f.client_nom}</p><p className="text-muted truncate">{f.client_email}</p></div> },
    { titre: "Objet", cellule: (f) => <Pill ton={f.objet_type === "libre" ? "gris" : "vert"}>{f.objet_libelle}</Pill> },
    { titre: "Montant", cellule: (f) => <div className="text-xs tabular-nums"><p className="text-dark font-semibold">{formatPrice(f.total_ttc)}</p>{f.tva > 0 && <p className="text-muted">dont TVA {formatPrice(f.tva)}</p>}</div> },
  ];

  // DRF returns line errors as a list per line: an overall message is enough
  const erreurLignes = erreurs.lignes ? "Vérifiez les lignes : désignation, quantité (au moins 1) et prix unitaire." : undefined;

  return (
    <div className="space-y-4">
      {societe && !societe.complets && (
        <div role="alert" className="flex flex-wrap items-center gap-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl px-4 py-3 text-sm">
          <AlertTriangle size={18} className="flex-shrink-0" aria-hidden />
          <span className="flex-1 min-w-[200px]">Aucune facture ne peut être émise tant que la raison sociale et l&apos;adresse de la société ne sont pas renseignées.</span>
          <button type="button" onClick={() => router.replace(`${pathname}?onglet=societe`)} className="font-bold underline">Compléter</button>
        </div>
      )}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <SearchInput value={q} onChange={setQ} placeholder="Numéro, client ou email" />
        <button type="button" onClick={ouvrir} className="flex-shrink-0 flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">
          <Plus size={16} aria-hidden /> Facture libre
        </button>
      </div>
      <p className="text-xs text-muted">
        Les factures des séjours, transferts et locations payés s&apos;émettent depuis leurs listes (bouton « Facture ») ou par le voyageur depuis son compte.
        Une facture émise n&apos;est jamais modifiée : la numérotation est continue.
      </p>

      <AdminTable colonnes={colonnes} lignes={data?.results} cle={(f) => f.id} titreMobile={(f) => colonnes[0].cellule(f)}
        actions={(f) => <ActionButton onClick={() => telecharger(f)} disabled={telechargement === f.id}>{telechargement === f.id ? "…" : "PDF"}</ActionButton>}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}

      <Panneau ouvert={ouvert} titre="Facture libre" onFermer={() => setOuvert(false)} onValider={emettre} envoi={envoi} libelle="Émettre la facture">
        <Champ label="Client" erreur={erreurs.client_nom}>
          <Saisie value={client.client_nom} onChange={(e) => setClient((c) => ({ ...c, client_nom: e.target.value }))} required placeholder="Nom ou raison sociale" />
        </Champ>
        <Champ label="Email" erreur={erreurs.client_email}>
          <Saisie type="email" value={client.client_email} onChange={(e) => setClient((c) => ({ ...c, client_email: e.target.value }))} />
        </Champ>
        <Champ label="Adresse" erreur={erreurs.client_adresse}>
          <Zone rows={2} value={client.client_adresse} onChange={(e) => setClient((c) => ({ ...c, client_adresse: e.target.value }))} />
        </Champ>

        <fieldset className="space-y-3">
          <legend className="text-xs font-bold text-dark uppercase tracking-wide mb-1.5">Lignes (montants TTC en FCFA)</legend>
          {lignes.map((l, i) => (
            <div key={i} className="rounded-xl border border-gray-100 p-3 space-y-2">
              <div className="flex gap-2">
                <Saisie aria-label={`Désignation, ligne ${i + 1}`} placeholder="Désignation" value={l.libelle} onChange={(e) => ligne(i, "libelle", e.target.value)} required />
                {lignes.length > 1 && (
                  <button type="button" onClick={() => setLignes((ls) => ls.filter((_, j) => j !== i))} aria-label={`Supprimer la ligne ${i + 1}`}
                    className="flex-shrink-0 w-11 rounded-xl border border-gray-200 text-gray-500 hover:text-red-600 hover:border-red-200 flex items-center justify-center">
                    <Trash2 size={16} aria-hidden />
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Saisie aria-label={`Quantité, ligne ${i + 1}`} type="number" min={1} inputMode="numeric" placeholder="Qté" value={l.quantite} onChange={(e) => ligne(i, "quantite", e.target.value)} required />
                <Saisie aria-label={`Prix unitaire, ligne ${i + 1}`} type="number" min={0} inputMode="numeric" placeholder="Prix unitaire" value={l.prix_unitaire} onChange={(e) => ligne(i, "prix_unitaire", e.target.value)} required />
              </div>
            </div>
          ))}
          {erreurLignes && <p role="alert" className="text-xs text-red-600">{erreurLignes}</p>}
          <button type="button" onClick={() => setLignes((ls) => [...ls, LIGNE_VIDE])} className="flex items-center gap-1.5 text-sm font-semibold text-primary">
            <Plus size={15} aria-hidden /> Ajouter une ligne
          </button>
        </fieldset>
        <div className="flex justify-between items-center bg-gray-50 rounded-xl px-4 py-3">
          <span className="text-sm text-muted">Total TTC</span>
          <span className="font-heading font-bold text-dark tabular-nums">{formatPrice(total)}</span>
        </div>
        {erreurs.detail && <p role="alert" className="text-sm text-red-600">{erreurs.detail}</p>}
      </Panneau>
    </div>
  );
}
