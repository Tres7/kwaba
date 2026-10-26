"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { HandHeart } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { Pill } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Liste, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import type { CauseGive, OngAdmin, ProjetAdmin } from "@/types/api/admin";

export const CAUSES: { value: CauseGive; label: string }[] = [
  { value: "education", label: "Éducation" }, { value: "sante", label: "Santé" },
  { value: "eau", label: "Accès à l'eau" }, { value: "environnement", label: "Environnement" },
];
const PAYS = [{ value: "TG", label: "Togo" }, { value: "BJ", label: "Bénin" }, { value: "BF", label: "Burkina Faso" },
  { value: "NE", label: "Niger" }, { value: "ML", label: "Mali" }];
// The API client sends JSON by default: header needed to send the photos
const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

type FormOng = Omit<OngAdmin, "id" | "logo" | "image" | "collecte" | "nb_dons" | "nb_projets" | "verifiee_le"> & { verifiee_le: string };
const ONG_VIDE: FormOng = { nom: "", slug: "", cause: "education", pays: "TG", ville: "", resume: "", description: "", site_web: "",
  numero_enregistrement: "", verifiee_le: "", verification: "", contact_nom: "", contact_email: "", contact_telephone: "",
  coordonnees_reversement: "", actif: true };
type FormProjet = { titre: string; cause: CauseGive; resume: string; description: string; lieu: string; objectif: string; actif: boolean };
const PROJET_VIDE: FormProjet = { titre: "", cause: "education", resume: "", description: "", lieu: "", objectif: "", actif: true };

/** FormData from an object; photos are only attached if a new one is chosen. */
function formulaire(valeurs: Record<string, unknown>, photos: Record<string, File | null>) {
  const corps = new FormData();
  for (const [k, v] of Object.entries(valeurs)) {
    if (v === null || v === undefined) continue;
    corps.append(k, typeof v === "boolean" ? (v ? "true" : "false") : String(v));
  }
  for (const [k, f] of Object.entries(photos)) if (f) corps.append(k, f);
  return corps;
}

export default function Organisations() {
  const queryClient = useQueryClient();
  const { data: ongs, isLoading } = useQuery({
    queryKey: ["admin", "give", "organisations"],
    queryFn: async () => (await api.get<OngAdmin[]>("/v1/admin/give/organisations/")).data,
  });
  const [edition, setEdition] = useState<OngAdmin | "nouvelle" | null>(null);
  const [form, setForm] = useState<FormOng>(ONG_VIDE);
  const [photos, setPhotos] = useState<{ logo: File | null; image: File | null }>({ logo: null, image: null });
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);

  // Projets de l'ONG ouverte
  const [ongProjets, setOngProjets] = useState<OngAdmin | null>(null);
  const [projet, setProjet] = useState<ProjetAdmin | "nouveau" | null>(null);
  const [formProjet, setFormProjet] = useState<FormProjet>(PROJET_VIDE);
  const [photoProjet, setPhotoProjet] = useState<File | null>(null);
  const { data: projets = [] } = useQuery({
    queryKey: ["admin", "give", "projets", ongProjets?.id],
    queryFn: async () => (await api.get<ProjetAdmin[]>(`/v1/admin/give/organisations/${ongProjets!.id}/projets/`)).data,
    enabled: !!ongProjets,
  });

  const champ = <K extends keyof FormOng>(k: K) => (v: FormOng[K]) => setForm((f) => ({ ...f, [k]: v }));

  const ouvrir = (o: OngAdmin | "nouvelle") => {
    setEdition(o);
    setForm(o === "nouvelle" ? ONG_VIDE : { ...o, verifiee_le: o.verifiee_le ?? "" });
    setPhotos({ logo: null, image: null });
    setErreurs({});
  };

  const enregistrer = async () => {
    setEnvoi(true);
    setErreurs({});
    const valeurs: Record<string, unknown> = { ...form, verifiee_le: form.verifiee_le || null };
    if (edition === "nouvelle" && !form.slug) delete valeurs.slug;
    try {
      if (edition === "nouvelle") await api.post("/v1/admin/give/organisations/", formulaire(valeurs, photos), MULTIPART);
      else if (edition) {
        await api.patch(`/v1/admin/give/organisations/${edition.id}/`, formulaire(valeurs, photos), MULTIPART);
        // Unpublish: empty date, which multipart cannot send
        if (!form.verifiee_le && edition.verifiee_le) await api.patch(`/v1/admin/give/organisations/${edition.id}/`, { verifiee_le: null });
      }
      toast.success("ONG enregistrée");
      setEdition(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "give"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const ouvrirProjet = (p: ProjetAdmin | "nouveau") => {
    setProjet(p);
    setFormProjet(p === "nouveau" ? PROJET_VIDE : { ...p, objectif: p.objectif ? String(p.objectif) : "" });
    setPhotoProjet(null);
    setErreurs({});
  };

  const enregistrerProjet = async () => {
    if (!ongProjets) return;
    setEnvoi(true);
    const valeurs = { ...formProjet, objectif: formProjet.objectif || null };
    try {
      if (projet === "nouveau") await api.post(`/v1/admin/give/organisations/${ongProjets.id}/projets/`, formulaire(valeurs, { image: photoProjet }), MULTIPART);
      else if (projet) await api.patch(`/v1/admin/give/projets/${projet.id}/`, formulaire(valeurs, { image: photoProjet }), MULTIPART);
      toast.success("Projet enregistré");
      setProjet(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "give"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <p className="text-sm text-muted">Une ONG n&apos;apparaît sur le site qu&apos;une fois vérifiée (date de vérification renseignée) et active.</p>
        <button onClick={() => ouvrir("nouvelle")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouvelle ONG</button>
      </div>
      {isLoading ? <div className="h-40 skeleton rounded-2xl" /> : (
        <ul className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {ongs?.map((o) => (
            <li key={o.id} className="bg-white rounded-2xl border border-gray-100 overflow-hidden flex flex-col">
              <div className="h-28 bg-primary/5 flex items-center justify-center">
                {o.image
                  // eslint-disable-next-line @next/next/no-img-element
                  ? <img src={o.image} alt="" className="w-full h-full object-cover" />
                  : <HandHeart size={32} className="text-primary/30" />}
              </div>
              <div className="p-4 flex-1 flex flex-col">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-heading font-bold text-dark truncate">{o.nom}</p>
                  <Pill ton={o.verifiee_le && o.actif ? "vert" : o.actif ? "orange" : "gris"}>{o.verifiee_le && o.actif ? "Publiée" : o.actif ? "À vérifier" : "Désactivée"}</Pill>
                </div>
                <p className="text-xs text-muted mt-0.5">{CAUSES.find((c) => c.value === o.cause)?.label} · {o.ville}</p>
                <p className="text-sm text-dark mt-2 tabular-nums">{formatPrice(o.collecte)} collectés · {o.nb_dons} don(s)</p>
                <div className="flex gap-2 mt-4">
                  <button type="button" onClick={() => ouvrir(o)} className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-gray-200 text-dark hover:bg-gray-50">Modifier</button>
                  <button type="button" onClick={() => { setOngProjets(o); setProjet(null); }} className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-gray-200 text-dark hover:bg-gray-50">
                    Projets ({o.nb_projets})
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Panneau ouvert={!!edition} titre={edition === "nouvelle" ? "Nouvelle ONG" : "Modifier l'ONG"} onFermer={() => setEdition(null)} onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <Champ label="Nom" erreur={erreurs.nom}><Saisie value={form.nom} onChange={(e) => champ("nom")(e.target.value)} required /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Cause"><Liste value={form.cause} onChange={(e) => champ("cause")(e.target.value as CauseGive)} options={CAUSES} /></Champ>
          <Champ label="Pays"><Liste value={form.pays} onChange={(e) => champ("pays")(e.target.value)} options={PAYS} /></Champ>
          <Champ label="Ville" erreur={erreurs.ville}><Saisie value={form.ville} onChange={(e) => champ("ville")(e.target.value)} required /></Champ>
          <Champ label="Adresse de la page" aide="Vide : déduite du nom" erreur={erreurs.slug}><Saisie value={form.slug} onChange={(e) => champ("slug")(e.target.value)} placeholder="ecoles-du-mono" /></Champ>
        </div>
        <Champ label="Résumé (carte)" erreur={erreurs.resume}><Saisie value={form.resume} onChange={(e) => champ("resume")(e.target.value)} maxLength={200} required /></Champ>
        <Champ label="Description" erreur={erreurs.description}><Zone rows={4} value={form.description} onChange={(e) => champ("description")(e.target.value)} required /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Photo de couverture" erreur={erreurs.image}><input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" onChange={(e) => setPhotos({ ...photos, image: e.target.files?.[0] ?? null })} /></Champ>
          <Champ label="Logo" erreur={erreurs.logo}><input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" onChange={(e) => setPhotos({ ...photos, logo: e.target.files?.[0] ?? null })} /></Champ>
        </div>
        <Champ label="Site web" erreur={erreurs.site_web}><Saisie type="url" value={form.site_web} onChange={(e) => champ("site_web")(e.target.value)} placeholder="https://" /></Champ>
        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Vérification (publique)</p>
        <Champ label="N° d'enregistrement officiel" erreur={erreurs.numero_enregistrement}><Saisie value={form.numero_enregistrement} onChange={(e) => champ("numero_enregistrement")(e.target.value)} required /></Champ>
        <Champ label="Ce qui a été vérifié" aide="Récépissé, statuts, compte bancaire, visite…" erreur={erreurs.verification}><Zone value={form.verification} onChange={(e) => champ("verification")(e.target.value)} /></Champ>
        <Champ label="Date de vérification" aide="Renseignée : l'ONG est publiée sur le site" erreur={erreurs.verifiee_le}>
          <Saisie type="date" value={form.verifiee_le} onChange={(e) => champ("verifiee_le")(e.target.value)} />
        </Champ>
        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Réservé à l&apos;équipe</p>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Contact"><Saisie value={form.contact_nom} onChange={(e) => champ("contact_nom")(e.target.value)} /></Champ>
          <Champ label="Téléphone"><Saisie type="tel" value={form.contact_telephone} onChange={(e) => champ("contact_telephone")(e.target.value)} /></Champ>
        </div>
        <Champ label="Email" erreur={erreurs.contact_email}><Saisie type="email" value={form.contact_email} onChange={(e) => champ("contact_email")(e.target.value)} /></Champ>
        <Champ label="Coordonnées de reversement" aide="IBAN / RIB ou Mobile Money au nom de l'ONG, jamais affiché sur le site">
          <Zone value={form.coordonnees_reversement} onChange={(e) => champ("coordonnees_reversement")(e.target.value)} />
        </Champ>
        <Interrupteur label="Active" checked={form.actif} onChange={champ("actif")} />
      </Panneau>

      <Panneau ouvert={!!ongProjets} titre={projet ? (projet === "nouveau" ? "Nouveau projet" : "Modifier le projet") : `Projets · ${ongProjets?.nom ?? ""}`}
        onFermer={() => (projet ? setProjet(null) : setOngProjets(null))} onValider={projet ? enregistrerProjet : () => ouvrirProjet("nouveau")}
        envoi={envoi} libelle={projet ? "Enregistrer" : "Nouveau projet"}>
        {!projet ? (
          projets.length ? (
            <ul className="space-y-2">
              {projets.map((p) => (
                <li key={p.id}>
                  <button type="button" onClick={() => ouvrirProjet(p)} className="w-full text-left rounded-xl border border-gray-100 p-3 hover:bg-gray-50">
                    <div className="flex justify-between gap-2"><span className="font-semibold text-dark">{p.titre}</span><Pill ton={p.actif ? "vert" : "gris"}>{p.actif ? "Actif" : "Inactif"}</Pill></div>
                    <p className="text-xs text-muted mt-0.5">{p.resume}{p.objectif ? ` · objectif ${formatPrice(p.objectif)}` : ""}</p>
                  </button>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted">Aucun projet pour l&apos;instant.</p>
        ) : (
          <>
            {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
            <Champ label="Titre" erreur={erreurs.titre}><Saisie value={formProjet.titre} onChange={(e) => setFormProjet({ ...formProjet, titre: e.target.value })} required /></Champ>
            <div className="grid grid-cols-2 gap-3">
              <Champ label="Cause"><Liste value={formProjet.cause} onChange={(e) => setFormProjet({ ...formProjet, cause: e.target.value as CauseGive })} options={CAUSES} /></Champ>
              <Champ label="Lieu"><Saisie value={formProjet.lieu} onChange={(e) => setFormProjet({ ...formProjet, lieu: e.target.value })} /></Champ>
            </div>
            <Champ label="Résumé" erreur={erreurs.resume}><Saisie value={formProjet.resume} onChange={(e) => setFormProjet({ ...formProjet, resume: e.target.value })} required maxLength={200} /></Champ>
            <Champ label="Description"><Zone value={formProjet.description} onChange={(e) => setFormProjet({ ...formProjet, description: e.target.value })} /></Champ>
            <Champ label="Objectif (FCFA, facultatif)" erreur={erreurs.objectif}><Saisie type="number" min={0} value={formProjet.objectif} onChange={(e) => setFormProjet({ ...formProjet, objectif: e.target.value })} /></Champ>
            <Champ label="Photo" erreur={erreurs.image}><input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" onChange={(e) => setPhotoProjet(e.target.files?.[0] ?? null)} /></Champ>
            <Interrupteur label="Actif (proposé aux donateurs)" checked={formProjet.actif} onChange={(v) => setFormProjet({ ...formProjet, actif: v })} />
          </>
        )}
      </Panneau>
    </div>
  );
}
