"use client";

import { useEffect, useState } from "react";
import { Compass, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { cn, formatPrice } from "@/lib/utils";
import { Pill } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Liste, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import type { CategorieExperience, ExperienceAdmin } from "@/types/api/admin";
import { creerExperience, modifierExperience, supprimerExperience } from "../api";
import { useExperiencesAdmin, useRafraichirExperiencesAdmin } from "../hooks";

export const CATEGORIES_EXPERIENCE: { value: CategorieExperience; label: string }[] = [
  { value: "activites", label: "Activité" }, { value: "restaurants", label: "Restaurant" },
  { value: "loisirs", label: "Loisir" }, { value: "sites", label: "Site touristique" },
];

type Formulaire = Omit<ExperienceAdmin, "id" | "photo" | "prix" | "ordre"> & { prix: string; ordre: string };
const VIDE: Formulaire = {
  categorie: "activites", nom: "", nom_en: "", etiquette: "", etiquette_en: "", ville: "", pays: "", pays_en: "",
  description: "", description_en: "", prix: "", gratuit: false, actif: true, ordre: "0",
};
const versFormulaire = (e: ExperienceAdmin): Formulaire => ({
  categorie: e.categorie, nom: e.nom, nom_en: e.nom_en, etiquette: e.etiquette, etiquette_en: e.etiquette_en, ville: e.ville,
  pays: e.pays, pays_en: e.pays_en, description: e.description, description_en: e.description_en,
  prix: e.prix === null ? "" : String(e.prix), gratuit: e.gratuit, actif: e.actif, ordre: String(e.ordre),
});

export default function Experiences() {
  const rafraichir = useRafraichirExperiencesAdmin();
  const { data: experiences, isLoading } = useExperiencesAdmin();
  const [filtre, setFiltre] = useState<CategorieExperience | "">("");
  const [edition, setEdition] = useState<ExperienceAdmin | "nouvelle" | null>(null);
  const [form, setForm] = useState<Formulaire>(VIDE);
  const [photo, setPhoto] = useState<File | null>(null);
  const [apercu, setApercu] = useState<string | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const champ = <K extends keyof Formulaire>(k: K) => (v: Formulaire[K]) => setForm((f) => ({ ...f, [k]: v }));

  // Preview of the chosen photo, released when it changes
  useEffect(() => {
    if (!photo) return setApercu(null);
    const url = URL.createObjectURL(photo);
    setApercu(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const ouvrir = (e: ExperienceAdmin | "nouvelle") => {
    setEdition(e);
    setForm(e === "nouvelle" ? VIDE : versFormulaire(e));
    setPhoto(null);
    setErreurs({});
  };

  const enregistrer = async () => {
    setEnvoi(true);
    setErreurs({});
    // Multipart (for the photo): booleans sent explicitly, empty price = no price
    const corps = new FormData();
    for (const [k, v] of Object.entries(form)) corps.append(k, typeof v === "boolean" ? (v ? "true" : "false") : String(v));
    if (photo) corps.append("image", photo);
    try {
      if (edition === "nouvelle") await creerExperience(corps);
      else if (edition) await modifierExperience(edition.id, corps);
      toast.success("Expérience enregistrée");
      setEdition(null);
      rafraichir();
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  const supprimer = async () => {
    if (!edition || edition === "nouvelle" || !window.confirm(`Supprimer « ${edition.nom} » ? Elle disparaît de la page Découvrir.`)) return;
    try {
      await supprimerExperience(edition.id);
      toast.success("Expérience supprimée");
      setEdition(null);
      rafraichir();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Suppression impossible."));
    }
  };

  const liste = (experiences ?? []).filter((e) => !filtre || e.categorie === filtre);
  const photoAffichee = apercu ?? (edition && edition !== "nouvelle" ? edition.photo : null);
  const puce = (actif: boolean) => cn("relative zone-tactile px-3 py-1.5 rounded-full text-xs font-bold border transition-colors",
    actif ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40");

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setFiltre("")} aria-pressed={!filtre} className={puce(!filtre)}>Toutes ({experiences?.length ?? 0})</button>
          {CATEGORIES_EXPERIENCE.map((c) => (
            <button key={c.value} type="button" onClick={() => setFiltre(c.value)} aria-pressed={filtre === c.value} className={puce(filtre === c.value)}>
              {c.label} ({experiences?.filter((e) => e.categorie === c.value).length ?? 0})
            </button>
          ))}
        </div>
        <button onClick={() => ouvrir("nouvelle")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouvelle expérience</button>
      </div>

      {isLoading ? <div className="h-40 skeleton rounded-2xl" /> : liste.length === 0 ? (
        <p className="bg-white rounded-2xl border border-gray-100 p-8 text-center text-sm text-muted">Aucune expérience dans cette catégorie.</p>
      ) : (
        <ul className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {liste.map((e) => (
            <li key={e.id}>
              <button type="button" onClick={() => ouvrir(e)} className="w-full text-left bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-card transition-shadow">
                <div className="h-32 bg-gray-100 flex items-center justify-center">
                  {e.photo
                    // eslint-disable-next-line @next/next/no-img-element
                    ? <img src={e.photo} alt="" className="w-full h-full object-cover" />
                    : <Compass size={36} className="text-gray-300" aria-hidden />}
                </div>
                <div className="p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-heading font-bold text-dark truncate">{e.nom}</p>
                    <Pill ton={e.actif ? "vert" : "gris"}>{e.actif ? "Publiée" : "Masquée"}</Pill>
                  </div>
                  <p className="text-xs text-muted mt-0.5">{CATEGORIES_EXPERIENCE.find((c) => c.value === e.categorie)?.label} · {e.etiquette} · {e.ville}, {e.pays}</p>
                  <p className="text-sm text-dark mt-2 tabular-nums">{e.gratuit ? "Gratuit" : e.prix !== null ? `≈ ${formatPrice(e.prix)}` : "Sans prix"}</p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      <Panneau ouvert={!!edition} titre={edition === "nouvelle" ? "Nouvelle expérience" : "Modifier l'expérience"} onFermer={() => setEdition(null)}
        onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Catégorie" erreur={erreurs.categorie}>
            <Liste value={form.categorie} onChange={(e) => champ("categorie")(e.target.value as CategorieExperience)} options={CATEGORIES_EXPERIENCE} />
          </Champ>
          <Champ label="Étiquette" aide="Culture, Plage, Ivoirien…" erreur={erreurs.etiquette}>
            <Saisie value={form.etiquette} onChange={(e) => champ("etiquette")(e.target.value)} maxLength={40} required />
          </Champ>
        </div>
        <Champ label="Nom" erreur={erreurs.nom}><Saisie value={form.nom} onChange={(e) => champ("nom")(e.target.value)} maxLength={120} required placeholder="Excursion à Ganvié" /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Ville" aide="Proposée dans le filtre des villes" erreur={erreurs.ville}><Saisie value={form.ville} onChange={(e) => champ("ville")(e.target.value)} required /></Champ>
          <Champ label="Pays" erreur={erreurs.pays}><Saisie value={form.pays} onChange={(e) => champ("pays")(e.target.value)} required /></Champ>
        </div>
        <Champ label="Description" erreur={erreurs.description}><Zone rows={3} value={form.description} onChange={(e) => champ("description")(e.target.value)} required /></Champ>
        <div className="grid grid-cols-2 gap-3 items-end">
          <Champ label="Prix indicatif (FCFA)" aide="Vide : pas de prix affiché" erreur={erreurs.prix}>
            <Saisie type="number" min={0} inputMode="numeric" value={form.gratuit ? "" : form.prix} disabled={form.gratuit} onChange={(e) => champ("prix")(e.target.value)} />
          </Champ>
          <Interrupteur label="Gratuit" checked={form.gratuit} onChange={champ("gratuit")} />
        </div>
        <Champ label="Photo" aide="JPEG, PNG ou WebP, 400 px minimum" erreur={erreurs.image}>
          <div className="space-y-2">
            {photoAffichee && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={photoAffichee} alt="" className="w-full h-36 object-cover rounded-xl bg-gray-100" />
            )}
            <input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          </div>
        </Champ>

        <p className="text-xs font-bold text-dark uppercase tracking-wide pt-2">Version anglaise (facultative)</p>
        <p className="text-xs text-muted -mt-1">Un champ vide affiche le texte français sur le site en anglais.</p>
        <Champ label="Nom en anglais" erreur={erreurs.nom_en}><Saisie value={form.nom_en} onChange={(e) => champ("nom_en")(e.target.value)} maxLength={120} /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Étiquette en anglais" erreur={erreurs.etiquette_en}><Saisie value={form.etiquette_en} onChange={(e) => champ("etiquette_en")(e.target.value)} maxLength={40} /></Champ>
          <Champ label="Pays en anglais" erreur={erreurs.pays_en}><Saisie value={form.pays_en} onChange={(e) => champ("pays_en")(e.target.value)} /></Champ>
        </div>
        <Champ label="Description en anglais" erreur={erreurs.description_en}><Zone rows={3} value={form.description_en} onChange={(e) => champ("description_en")(e.target.value)} /></Champ>

        <Champ label="Ordre d'affichage" aide="Les plus petits d'abord" erreur={erreurs.ordre}><Saisie type="number" min={0} value={form.ordre} onChange={(e) => champ("ordre")(e.target.value)} /></Champ>
        <Interrupteur label="Publiée sur la page Découvrir" checked={form.actif} onChange={champ("actif")} />
        {edition && edition !== "nouvelle" && (
          <button type="button" onClick={supprimer} className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-red-600 hover:underline">
            <Trash2 size={15} aria-hidden /> Supprimer l&apos;expérience
          </button>
        )}
      </Panneau>
    </div>
  );
}

