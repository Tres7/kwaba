"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Car, Images } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { formatDate, formatPrice, isoDate } from "@/lib/utils";
import { Pill } from "@/components/backoffice/AdminTable";
import Panneau, { Champ, Interrupteur, Liste, Saisie, Zone, erreursApi } from "@/components/backoffice/Panneau";
import PhotosVehicule, { envoyerPhotoVehicule, liberer, type FichierEnAttente } from "@/components/backoffice/location/PhotosVehicule";
import type { CategorieVehicule, Loueur, PhotoVehicule } from "@/types/api/admin";

const GAMMES = [["citadine", "Citadine"], ["berline", "Berline"], ["suv", "SUV"], ["4x4", "4x4 tout-terrain"], ["minibus", "Minibus"], ["utilitaire", "Utilitaire"]];
const BOITES = [["manuelle", "Manuelle"], ["automatique", "Automatique"]];
const CARBURANTS = [["essence", "Essence"], ["diesel", "Diesel"], ["hybride", "Hybride"], ["electrique", "Électrique"]];
const CAUTIONS = [["0", "Sans caution (badge « Sans caution »)"], ["1", "Une journée de location"], ["2", "Deux journées de location"]];
const opts = (l: string[][]) => l.map(([value, label]) => ({ value, label }));
const CAUTION_MAX = 100000;

type Texte = "prix_jour" | "places" | "bagages" | "ordre" | "annee" | "proprietaire" | "caution_jours" | "assurance_fin" | "visite_technique_fin";
type Formulaire = Omit<CategorieVehicule, "id" | "photos" | "caution" | Texte> & Record<Texte, string>;
const VIDE: Formulaire = {
  nom: "", gamme: "berline", exemple_modele: "", description: "", places: "5", bagages: "2", boite: "manuelle", carburant: "essence",
  climatisation: true, proprietaire: "", prix_jour: "", sans_chauffeur: true, avec_chauffeur: true, caution_jours: "0",
  immatriculation: "", annee: "", assurance_fin: "", visite_technique_fin: "", actif: false, ordre: "0",
};
const versFormulaire = (c: CategorieVehicule): Formulaire => ({
  ...c, places: String(c.places), bagages: String(c.bagages), ordre: String(c.ordre), caution_jours: String(c.caution_jours),
  prix_jour: c.prix_jour ? String(c.prix_jour) : "", proprietaire: c.proprietaire ? String(c.proprietaire) : "",
  annee: c.annee ? String(c.annee) : "", assurance_fin: c.assurance_fin ?? "", visite_technique_fin: c.visite_technique_fin ?? "",
});

/** An expired document removes the vehicle from the site (owner contract, art. 1). */
function expire(date: string | null) {
  return !!date && date < isoDate();
}

/** Partner owners' vehicles: their price, deposit, options and papers. */
export default function Categories() {
  const queryClient = useQueryClient();
  const { data: categories, isLoading } = useQuery({
    queryKey: ["admin", "location", "categories"],
    queryFn: async () => (await api.get<CategorieVehicule[]>("/v1/admin/location/categories/")).data,
  });
  const { data: proprietaires } = useQuery({
    queryKey: ["admin", "location", "loueurs"],
    queryFn: async () => (await api.get<Loueur[]>("/v1/admin/location/loueurs/")).data,
  });
  const [edition, setEdition] = useState<CategorieVehicule | "nouvelle" | null>(null);
  const [form, setForm] = useState<Formulaire>(VIDE);
  const [photos, setPhotos] = useState<PhotoVehicule[]>([]);
  const [enAttente, setEnAttente] = useState<FichierEnAttente[]>([]);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const champ = <K extends keyof Formulaire>(k: K) => (v: Formulaire[K]) => setForm((f) => ({ ...f, [k]: v }));
  const nomProprietaire = (id: number | null) => proprietaires?.find((p) => p.id === id)?.nom;
  const caution = Math.min(Number(form.caution_jours) * (Number(form.prix_jour) || 0), CAUTION_MAX);

  const ouvrir = (c: CategorieVehicule | "nouvelle") => {
    setEdition(c);
    setForm(c === "nouvelle" ? VIDE : versFormulaire(c));
    setPhotos(c === "nouvelle" ? [] : c.photos);
    liberer(enAttente);
    setEnAttente([]);
    setErreurs({});
  };

  const fermer = () => {
    liberer(enAttente);
    setEnAttente([]);
    setEdition(null);
  };

  // Photos added, removed or reordered: the vehicle list (thumbnails) follows
  const surPhotos = (liste: PhotoVehicule[]) => {
    setPhotos(liste);
    queryClient.invalidateQueries({ queryKey: ["admin", "location", "categories"] });
  };

  const enregistrer = async () => {
    setEnvoi(true);
    setErreurs({});
    // Empty fields: null; photos have their own requests
    const champs = Object.fromEntries(Object.entries(form).filter(([k]) => k !== "id" && k !== "photos"));
    const corps = {
      ...champs, prix_jour: form.prix_jour || null, proprietaire: form.proprietaire ? Number(form.proprietaire) : null,
      caution_jours: Number(form.caution_jours), annee: form.annee ? Number(form.annee) : null,
      assurance_fin: form.assurance_fin || null, visite_technique_fin: form.visite_technique_fin || null,
    };
    try {
      if (edition === "nouvelle") {
        const creee = (await api.post<CategorieVehicule>("/v1/admin/location/categories/", corps)).data;
        // Photos chosen before the creation: sent now, one after the other
        const echecs: string[] = [];
        for (const f of enAttente) {
          try {
            await envoyerPhotoVehicule(creee.id, f.fichier);
          } catch (err) {
            echecs.push(`${f.fichier.name} : ${apiErrorMessage(err, "envoi impossible")}`);
          }
        }
        if (echecs.length) toast.error(`Véhicule créé, mais ${echecs.length} photo(s) non envoyée(s). ${echecs.join(" ; ")}`, { duration: 10000 });
      } else if (edition) {
        await api.patch(`/v1/admin/location/categories/${edition.id}/`, corps);
      }
      toast.success("Véhicule enregistré");
      fermer();
      queryClient.invalidateQueries({ queryKey: ["admin", "location"] });
    } catch (err) {
      setErreurs(erreursApi(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center gap-3">
        <p className="text-sm text-muted">
          Chaque véhicule appartient à un propriétaire partenaire, qui fixe son prix par jour et sa caution. Le chauffeur est facturé
          à part (7 000 FCFA par jour). Un véhicule n&apos;est proposé qu&apos;actif, avec un prix et des papiers à jour.
        </p>
        <button onClick={() => ouvrir("nouvelle")} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">Nouveau véhicule</button>
      </div>
      {isLoading ? <div className="h-40 skeleton rounded-2xl" /> : (
        <ul className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {categories?.map((c) => {
            const papiersExpires = expire(c.assurance_fin) || expire(c.visite_technique_fin);
            return (
              <li key={c.id}>
                <button type="button" onClick={() => ouvrir(c)} className="w-full text-left bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-card transition-shadow">
                  <div className="relative h-32 bg-gray-100 flex items-center justify-center">
                    {c.photos[0]
                      // eslint-disable-next-line @next/next/no-img-element
                      ? <img src={c.photos[0].url} alt="" className="w-full h-full object-cover" />
                      : <Car size={36} className="text-gray-300" />}
                    {c.photos.length > 1 && (
                      <span className="absolute bottom-2 right-2 flex items-center gap-1 bg-black/60 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                        <Images size={12} aria-hidden /> {c.photos.length}
                      </span>
                    )}
                  </div>
                  <div className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-heading font-bold text-dark">{c.nom}</p>
                      <Pill ton={papiersExpires ? "rouge" : c.actif ? "vert" : "gris"}>{papiersExpires ? "Papiers expirés" : c.actif ? "Proposé" : "Désactivé"}</Pill>
                    </div>
                    <p className="text-xs text-muted mt-0.5">{c.exemple_modele || "-"} · {c.places} places · {nomProprietaire(c.proprietaire) ?? "sans propriétaire"}</p>
                    <p className="text-sm text-dark mt-2 tabular-nums">
                      {c.prix_jour ? `${formatPrice(c.prix_jour)} / jour` : "Prix à renseigner"} · {c.caution ? `caution ${formatPrice(c.caution)}` : "sans caution"}
                    </p>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <Panneau ouvert={!!edition} titre={edition === "nouvelle" ? "Nouveau véhicule" : "Modifier le véhicule"} onFermer={fermer} onValider={enregistrer} envoi={envoi}>
        {erreurs.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{erreurs.detail}</p>}
        <Champ label="Propriétaire" aide="Jamais montré au voyageur" erreur={erreurs.proprietaire}>
          <Liste value={form.proprietaire} onChange={(e) => champ("proprietaire")(e.target.value)}
            options={[{ value: "", label: "Choisir un propriétaire" }, ...(proprietaires ?? []).map((p) => ({ value: String(p.id), label: p.nom }))]} />
        </Champ>
        <Champ label="Nom affiché" erreur={erreurs.nom}><Saisie value={form.nom} onChange={(e) => champ("nom")(e.target.value)} required maxLength={80} placeholder="Toyota RAV4 2019" /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Gamme"><Liste value={form.gamme} onChange={(e) => champ("gamme")(e.target.value as Formulaire["gamme"])} options={opts(GAMMES)} /></Champ>
          <Champ label="Marque et modèle"><Saisie value={form.exemple_modele} onChange={(e) => champ("exemple_modele")(e.target.value)} placeholder="Toyota RAV4" /></Champ>
          <Champ label="Année"><Saisie type="number" min={1980} max={2100} value={form.annee} onChange={(e) => champ("annee")(e.target.value)} /></Champ>
          <Champ label="Immatriculation"><Saisie value={form.immatriculation} onChange={(e) => champ("immatriculation")(e.target.value)} maxLength={20} placeholder="TG 1234 AB" /></Champ>
          <Champ label="Places" erreur={erreurs.places}><Saisie type="number" min={1} value={form.places} onChange={(e) => champ("places")(e.target.value)} required /></Champ>
          <Champ label="Valises" erreur={erreurs.bagages}><Saisie type="number" min={0} value={form.bagages} onChange={(e) => champ("bagages")(e.target.value)} required /></Champ>
          <Champ label="Boîte"><Liste value={form.boite} onChange={(e) => champ("boite")(e.target.value as Formulaire["boite"])} options={opts(BOITES)} /></Champ>
          <Champ label="Carburant"><Liste value={form.carburant} onChange={(e) => champ("carburant")(e.target.value as Formulaire["carburant"])} options={opts(CARBURANTS)} /></Champ>
        </div>
        <Champ label="Description"><Zone value={form.description} onChange={(e) => champ("description")(e.target.value)} /></Champ>
        <div className="grid grid-cols-2 gap-3">
          <Champ label="Prix par jour (FCFA)" aide="Fixé par le propriétaire, sans le chauffeur" erreur={erreurs.prix_jour}>
            <Saisie type="number" min={0} inputMode="numeric" value={form.prix_jour} onChange={(e) => champ("prix_jour")(e.target.value)} />
          </Champ>
          <Champ label="Caution (voiture seule)" aide={`Soit ${formatPrice(caution)} (100 000 au plus), payée en ligne`}>
            <Liste value={form.caution_jours} onChange={(e) => champ("caution_jours")(e.target.value)} options={opts(CAUTIONS)} />
          </Champ>
          <Champ label="Assurance valable jusqu'au" aide={form.assurance_fin ? `Retiré du site après le ${formatDate(form.assurance_fin)}` : undefined}>
            <Saisie type="date" value={form.assurance_fin} onChange={(e) => champ("assurance_fin")(e.target.value)} />
          </Champ>
          <Champ label="Visite technique jusqu'au">
            <Saisie type="date" value={form.visite_technique_fin} onChange={(e) => champ("visite_technique_fin")(e.target.value)} />
          </Champ>
          <Champ label="Ordre d'affichage"><Saisie type="number" min={0} value={form.ordre} onChange={(e) => champ("ordre")(e.target.value)} /></Champ>
        </div>
        <Champ label="Photos du véhicule" aide="JPEG, PNG ou WebP, 400 px minimum. La première est la photo principale.">
          <PhotosVehicule categorieId={edition && edition !== "nouvelle" ? edition.id : null} photos={photos} onPhotos={surPhotos}
            enAttente={enAttente} onEnAttente={setEnAttente} />
        </Champ>
        <Interrupteur label="Proposé sans chauffeur (le voyageur conduit)" checked={form.sans_chauffeur} onChange={champ("sans_chauffeur")} />
        <Interrupteur label="Proposé avec chauffeur" checked={form.avec_chauffeur} onChange={champ("avec_chauffeur")} />
        <Interrupteur label="Climatisation" checked={form.climatisation} onChange={champ("climatisation")} />
        <Interrupteur label="Proposé aux voyageurs" checked={form.actif} onChange={champ("actif")} />
        {erreurs.actif && <p role="alert" className="text-xs text-red-600">{erreurs.actif}</p>}
      </Panneau>
    </div>
  );
}
