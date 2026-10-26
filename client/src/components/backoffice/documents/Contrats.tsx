"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { messageErreurPdf, telechargerPdf } from "@/lib/documents";
import { cn, formatDate } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import AdminTable, { ActionButton, Pagination, Pill, SearchInput, type Colonne } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import Panneau, { Champ, Liste, Saisie, erreursApi } from "@/components/backoffice/Panneau";
import Select from "@/components/ui/Select";
import type { ContratAdmin, PartieContrat } from "@/types/api/admin";
import type { TypeContrat } from "@/types/api/contrat";

export const TYPES: { value: TypeContrat; label: string }[] = [
  { value: "hote", label: "Hôte particulier" }, { value: "hotel", label: "Hôtel" }, { value: "loueur", label: "Propriétaire de véhicule" },
  { value: "chauffeur", label: "Chauffeur" }, { value: "ong", label: "ONG (Kwa-Ba Give)" },
];
const FILTRE_TYPES = [{ value: "", label: "Tous les types" }, ...TYPES];
const STATUTS = [{ value: "", label: "Tous" }, { value: "a_signer", label: "À signer" }, { value: "signe", label: "Signés" }, { value: "annule", label: "Annulés" }];
const date = (d: string | null) => (d ? formatDate(d, { day: "numeric", month: "short", year: "numeric" }) : "-");

/** Issued contracts: sending for signature, reminder, cancellation, signed PDF with certificate. */
export default function Contrats() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [statut, setStatut] = useState("");
  const recherche = useDebounced(q);
  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<ContratAdmin>("contrats", { q: recherche, type, statut });
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [telechargement, setTelechargement] = useState<string | null>(null);

  // Nouveau contrat
  const [ouvert, setOuvert] = useState(false);
  const [typeNouveau, setTypeNouveau] = useState<TypeContrat>("chauffeur");
  const [recherchePartie, setRecherchePartie] = useState("");
  const [partie, setPartie] = useState<PartieContrat | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const qPartie = useDebounced(recherchePartie);
  const { data: parties, isFetching: chargementParties } = useQuery({
    queryKey: ["admin", "contrats-parties", typeNouveau, qPartie],
    queryFn: async () => (await api.get<PartieContrat[]>("/v1/admin/contrats/parties/", { params: { type: typeNouveau, q: qPartie } })).data,
    enabled: ouvert,
  });

  const rafraichir = () => queryClient.invalidateQueries({ queryKey: ["admin", "contrats"] });

  const telecharger = async (c: ContratAdmin) => {
    setTelechargement(c.id);
    try {
      await telechargerPdf(`/v1/admin/contrats/${c.id}/pdf/`, `contrat-${c.reference}.pdf`);
    } catch (err) {
      toast.error(await messageErreurPdf(err));
    } finally {
      setTelechargement(null);
    }
  };

  const envoyer = async () => {
    if (!partie) return setErreurs({ partie_id: "Choisissez la partie qui signera." });
    setEnvoi(true);
    setErreurs({});
    try {
      const { data: c } = await api.post<ContratAdmin>("/v1/admin/contrats/", { type: typeNouveau, partie_id: partie.id });
      toast.success(`Contrat ${c.reference} envoyé à ${c.partie_email}`);
      setOuvert(false);
      rafraichir();
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const action = async (c: ContratAdmin, nom: "renvoyer" | "annuler", motif?: string) => {
    try {
      await api.post(`/v1/admin/contrats/${c.id}/${nom}/`, motif ? { motif } : {});
      toast.success(nom === "renvoyer" ? `Nouveau lien envoyé à ${c.partie_email}` : "Contrat annulé");
      rafraichir();
    } catch (err) {
      toast.error(apiErrorMessage(err));
      throw err;
    }
  };

  const colonnes: Colonne<ContratAdmin>[] = [
    { titre: "Contrat", masquerMobile: true, cellule: (c) => <div className="min-w-0"><p className="font-semibold text-dark truncate">{c.type_libelle}</p><p className="text-xs text-muted font-mono">{c.reference} · v{c.version_modele}</p></div> },
    { titre: "Partie", cellule: (c) => <div className="text-xs min-w-0"><p className="text-dark font-medium truncate">{c.partie_nom}</p><p className="text-muted truncate">{c.partie_email || "-"}</p></div> },
    {
      titre: "Statut", cellule: (c) => (
        <div className="space-y-1">
          <Pill ton={c.statut === "signe" ? "vert" : c.statut === "annule" ? "gris" : c.expire ? "rouge" : "orange"}>
            {c.statut === "a_signer" && c.expire ? "Lien expiré" : c.statut_libelle}
          </Pill>
          {c.statut === "annule" && c.motif_annulation && <p className="text-xs text-muted max-w-[200px] truncate" title={c.motif_annulation}>{c.motif_annulation}</p>}
        </div>
      ),
    },
    {
      titre: "Dates", cellule: (c) => (
        <div className="text-xs whitespace-nowrap">
          <p>Émis le {date(c.cree_le)}</p>
          {c.signe_le ? <p className="text-green-700 font-medium">Signé le {date(c.signe_le)}</p>
            : c.statut === "a_signer" && <p className="text-muted">{c.envoye_le ? `Lien valable jusqu'au ${date(c.expire_le)}` : "Signature dans l'espace hôte"}</p>}
        </div>
      ),
    },
  ];

  const actions = (c: ContratAdmin) => (
    <>
      <ActionButton onClick={() => telecharger(c)} disabled={telechargement === c.id}>{telechargement === c.id ? "…" : "PDF"}</ActionButton>
      {c.statut === "a_signer" && c.partie_email && (
        <ActionButton onClick={() => setConfirmation({
          titre: "Renvoyer le lien de signature",
          message: <>Un nouveau lien, valable 30 jours, sera envoyé à <strong>{c.partie_email}</strong>. L&apos;ancien ne fonctionnera plus.</>,
          libelle: "Renvoyer", action: () => action(c, "renvoyer"),
        })}>Renvoyer</ActionButton>
      )}
      {c.statut !== "annule" && (
        <ActionButton danger onClick={() => setConfirmation({
          titre: "Annuler le contrat",
          message: c.statut === "signe"
            ? <>Le contrat signé <strong>{c.reference}</strong> sera marqué comme résilié. Le PDF signé reste consultable. Un nouveau contrat pourra être émis.</>
            : <>Le lien de signature de <strong>{c.reference}</strong> ne fonctionnera plus.</>,
          libelle: "Annuler le contrat", danger: true, motif: true, action: (motif) => action(c, "annuler", motif),
        })}>Annuler</ActionButton>
      )}
    </>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
        <SearchInput value={q} onChange={setQ} placeholder="Référence, partie ou email" />
        <Select label="Type" value={type} onChange={setType} options={FILTRE_TYPES} className="lg:w-52" />
        <Select label="Statut" value={statut} onChange={setStatut} options={STATUTS} className="lg:w-40" />
        <button type="button" onClick={() => { setOuvert(true); setPartie(null); setRecherchePartie(""); setErreurs({}); }}
          className="flex-shrink-0 flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">
          <Send size={16} aria-hidden /> Envoyer un contrat
        </button>
      </div>
      <p className="text-xs text-muted">
        Chaque contrat est pré-rempli à partir de son modèle (onglet Modèles de contrat) et des informations société, puis signé en ligne par lien personnel.
        Les hôtes signent le leur depuis leur espace : la visite de leur logement n&apos;est proposée aux agents qu&apos;une fois le contrat signé.
      </p>

      <AdminTable colonnes={colonnes} lignes={data?.results} cle={(c) => c.id} titreMobile={(c) => colonnes[0].cellule(c)} actions={actions}
        chargement={isLoading || isFetching} erreur={isError} onReessayer={refetch} />
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}

      <Panneau ouvert={ouvert} titre="Envoyer un contrat à signer" onFermer={() => setOuvert(false)} onValider={envoyer} envoi={envoi} libelle="Envoyer pour signature">
        <Champ label="Type de contrat">
          <Liste value={typeNouveau} options={TYPES} onChange={(e) => { setTypeNouveau(e.target.value as TypeContrat); setPartie(null); setRecherchePartie(""); }} />
        </Champ>
        <Champ label="Partie" erreur={erreurs.partie_id}>
          <Saisie value={recherchePartie} onChange={(e) => setRecherchePartie(e.target.value)} placeholder="Rechercher par nom" type="search" />
        </Champ>
        <div role="radiogroup" aria-label="Partie" className={cn("space-y-1.5 max-h-72 overflow-y-auto", chargementParties && "opacity-60")}>
          {parties?.length === 0 && <p className="text-sm text-muted">Aucun résultat.</p>}
          {parties?.map((p) => {
            const occupe = p.contrat !== null;
            return (
              <label key={p.id} className={cn("flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm",
                occupe ? "border-gray-100 bg-gray-50 text-muted cursor-not-allowed" : "cursor-pointer hover:border-primary",
                partie?.id === p.id ? "border-primary bg-primary/5" : "border-gray-200")}>
                <input type="radio" name="partie" className="accent-primary" disabled={occupe} checked={partie?.id === p.id} onChange={() => setPartie(p)} />
                <span className="flex-1 min-w-0">
                  <span className="block font-semibold text-dark truncate">{p.nom}</span>
                  <span className={cn("block text-xs truncate", !p.email && "text-red-600")}>{p.email || "Pas d'email : à ajouter avant l'envoi"}</span>
                </span>
                {occupe && <Pill ton={p.contrat === "signe" ? "vert" : "orange"}>{p.contrat === "signe" ? "Signé" : "En cours"}</Pill>}
              </label>
            );
          })}
        </div>
        {erreurs.detail && <p role="alert" className="text-sm text-red-600">{erreurs.detail}</p>}
        <p className="text-xs text-muted">Le lien de signature, personnel et valable 30 jours, part par email. Le PDF signé est envoyé aux deux parties.</p>
      </Panneau>
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}
