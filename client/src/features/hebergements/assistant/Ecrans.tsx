"use client";

import { useCallback, type ComponentType } from "react";
import { useTranslations } from "next-intl";
import { Camera, Check, Sun } from "lucide-react";
import { ChoixPosition, type PointCarte } from "@/features/carte";
import Stepper from "@/components/ui/Stepper";
import { useFormat } from "@/lib/format";
import { QUARTIERS_LOME } from "@/lib/quartiers";
import { cn } from "@/lib/utils";
import type { HebergementType } from "@/types/api/models";
import { useEquipements } from "../AmenityBadge";
import type { DonneesAnnonce } from "../brouillons";
import PhotoUploader from "../PhotoUploader";
import { EcranAccueil, EcranContrat, EcranIdentite, EcranPrix, EcranRecapitulatif, EcranRegles, EcranSecurite, EcranTelephone, EcranVersement } from "./EcransFin";
import { MAX_DESCRIPTION, MAX_TITRE, MIN_DESCRIPTION, MIN_PHOTOS, type CleEtape, type Conditions } from "./etapes";

export interface EcranProps {
  donnees: DonneesAnnonce;
  modifier: (champs: DonneesAnnonce) => void;
  erreurs: Record<string, string[]>;
  /** Photos being sent: the host waits before going on */
  onOccupe: (occupe: boolean) => void;
  conditions?: Conditions;
}

const TYPES: HebergementType[] = ["maison", "appartement", "villa", "hotel", "residence", "auberge"];
const VILLES = ["Lomé", "Kpalimé", "Aného", "Atakpamé", "Sokodé", "Kara"];
export const champClass = "w-full px-4 py-3.5 bg-white border border-gray-200 rounded-2xl text-base text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";
export const libelleClass = "block text-sm font-semibold text-dark mb-2";

export function Question({ cle, children }: { cle: string; children?: React.ReactNode }) {
  const t = useTranslations("assistantHote");
  return (
    <>
      <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl leading-tight">{t(`${cle}.titre`)}</h1>
      {t.has(`${cle}.texte`) && <p className="text-gray-600 mt-2 mb-6">{t(`${cle}.texte`)}</p>}
      <div className={cn(!t.has(`${cle}.texte`) && "mt-6")}>{children}</div>
    </>
  );
}

export function Erreur({ messages }: { messages?: string[] }) {
  return messages?.length ? <p role="alert" className="text-sm text-red-700 mt-2">{messages[0]}</p> : null;
}

function Compteur({ valeur, max }: { valeur: number; max: number }) {
  return <p className={cn("text-xs text-right mt-1.5", valeur > max ? "text-red-700 font-semibold" : "text-gray-500")}>{valeur} / {max}</p>;
}

/** Big illustrated choice, one per option: the question is answered with one touch. */
function CarteChoix({ image, titre, texte, choisi, onChoisir }: {
  image: string; titre: string; texte: string; choisi: boolean; onChoisir: () => void;
}) {
  return (
    <button
      type="button" role="radio" aria-checked={choisi} onClick={onChoisir}
      className={cn(
        "group relative text-left rounded-3xl border-2 p-2 transition-all duration-200 motion-safe:hover:-translate-y-0.5",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        choisi ? "border-primary bg-primary-50 shadow-md" : "border-gray-100 bg-white hover:border-primary/40 hover:shadow-md",
      )}
    >
      <span className="block rounded-2xl overflow-hidden bg-light-muted">
        <img src={image} alt="" width={400} height={400} loading="lazy"
          className="w-full aspect-[4/3] object-cover transition-transform duration-300 motion-safe:group-hover:scale-105" />
      </span>
      <span className="block px-2 pt-2.5 pb-2">
        <span className="block font-heading font-bold text-dark text-sm sm:text-base">{titre}</span>
        <span className="block text-xs text-gray-500 mt-0.5 leading-snug">{texte}</span>
      </span>
      {choisi && (
        <span className="absolute top-3.5 right-3.5 w-7 h-7 rounded-full bg-primary text-white flex items-center justify-center shadow">
          <Check size={16} aria-hidden />
        </span>
      )}
    </button>
  );
}

function EcranType({ donnees, modifier }: EcranProps) {
  const { TYPE_LABELS } = useFormat();
  const t = useTranslations("assistantHote");
  const tAnnonce = useTranslations("annonce");
  return (
    <Question cle="type">
      <div role="radiogroup" aria-label={t("type.titre")} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {TYPES.map((type) => (
          <CarteChoix key={type} image={`/hote/type-${type}.webp`} titre={TYPE_LABELS[type]} texte={tAnnonce(`types.${type}`)}
            choisi={donnees.type === type} onChoisir={() => modifier({ type })} />
        ))}
      </div>
    </Question>
  );
}

function EcranEspace({ donnees, modifier }: EcranProps) {
  const t = useTranslations("assistantHote");
  return (
    <Question cle="espace">
      <div role="radiogroup" aria-label={t("espace.titre")} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <CarteChoix image="/hote/espace-entier.webp" titre={t("espace.entier.titre")} texte={t("espace.entier.texte")}
          choisi={donnees.espace === "entier"} onChoisir={() => modifier({ espace: "entier" })} />
        <CarteChoix image="/hote/espace-chambre.webp" titre={t("espace.chambre.titre")} texte={t("espace.chambre.texte")}
          choisi={donnees.espace === "chambre_privee"} onChoisir={() => modifier({ espace: "chambre_privee" })} />
      </div>
    </Question>
  );
}

function EcranAdresse({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("annonce");
  return (
    <Question cle="adresse">
      <div className="space-y-5">
        <div>
          <label className={libelleClass} htmlFor="a-ville">{t("ville")}</label>
          <input id="a-ville" className={champClass} value={donnees.city ?? ""} maxLength={100} autoComplete="address-level2"
            onChange={(e) => modifier({ city: e.target.value })} placeholder="Lomé" />
          <div className="flex flex-wrap gap-2 mt-3">
            {VILLES.map((ville) => (
              <button key={ville} type="button" aria-pressed={donnees.city === ville} onClick={() => modifier({ city: ville })}
                className={cn("px-3.5 py-1.5 rounded-full text-sm border transition-colors",
                  donnees.city === ville ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}>
                {ville}
              </button>
            ))}
          </div>
          <Erreur messages={erreurs.city} />
        </div>
        <div>
          <label className={libelleClass} htmlFor="a-quartier">{t("quartier")}</label>
          <input id="a-quartier" className={champClass} value={donnees.location ?? ""} maxLength={200} list="a-quartiers"
            onChange={(e) => modifier({ location: e.target.value })} placeholder="Bè Kpota" />
          {donnees.city === "Lomé" && <datalist id="a-quartiers">{QUARTIERS_LOME.map((q) => <option key={q} value={q} />)}</datalist>}
          <Erreur messages={erreurs.location} />
        </div>
      </div>
    </Question>
  );
}

function EcranPosition({ donnees, modifier, erreurs }: EcranProps) {
  const position = donnees.latitude != null && donnees.longitude != null
    ? { lat: Number(donnees.latitude), lng: Number(donnees.longitude) } : null;
  const placer = useCallback((p: PointCarte) => modifier({ latitude: p.lat, longitude: p.lng }), [modifier]);
  return (
    <Question cle="position">
      <ChoixPosition valeur={position} onChange={placer} ville={donnees.city ?? ""} />
      <Erreur messages={erreurs.latitude} />
    </Question>
  );
}

function EcranCapacite({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("annonce");
  const ligne = "py-3.5 border-b border-gray-100";
  return (
    <Question cle="capacite">
      <Stepper className={ligne} label={t("voyageursMax")} value={donnees.max_guests ?? 2} min={1} max={50}
        onChange={(n) => modifier({ max_guests: n })} />
      <Stepper className={ligne} label={t("chambres")} value={donnees.chambres ?? 1} min={0} max={50}
        onChange={(n) => modifier({ chambres: n })} />
      <Stepper className={ligne} label={t("sallesDeBain")} value={donnees.salles_de_bain ?? 1} min={0} max={50}
        onChange={(n) => modifier({ salles_de_bain: n })} />
      <Stepper className={ligne} label={t("litsDoubles")} value={donnees.lits_doubles ?? 0} min={0} max={50}
        onChange={(n) => modifier({ lits_doubles: n })} />
      <Stepper className={ligne} label={t("litsSimples")} value={donnees.lits_simples ?? 0} min={0} max={50}
        onChange={(n) => modifier({ lits_simples: n })} />
      <Stepper className={ligne} label={t("canapesLits")} value={donnees.canapes_lits ?? 0} min={0} max={50}
        onChange={(n) => modifier({ canapes_lits: n })} />
      <div className="mt-5">
        <label className={libelleClass} htmlFor="a-surface">{t("surface")}</label>
        <input id="a-surface" type="number" min={5} step={1} inputMode="numeric" className={champClass} placeholder="80"
          value={donnees.surface_m2 ?? ""} onChange={(e) => modifier({ surface_m2: e.target.value ? Number(e.target.value) : null })} />
        <Erreur messages={erreurs.surface_m2} />
      </div>
    </Question>
  );
}

function EcranEquipements({ donnees, modifier }: EcranProps) {
  const { CATEGORIES_EQUIPEMENTS } = useEquipements();
  const choisis = donnees.amenities ?? [];
  const basculer = (id: string) => modifier({ amenities: choisis.includes(id) ? choisis.filter((a) => a !== id) : [...choisis, id] });
  return (
    <Question cle="equipements">
      <div className="space-y-6">
        {CATEGORIES_EQUIPEMENTS.map((categorie) => (
          <fieldset key={categorie.id}>
            <legend className="text-sm font-semibold text-dark mb-2.5">{categorie.label}</legend>
            <div className="grid grid-cols-2 gap-2">
              {categorie.equipements.map(({ id, label, Icone }) => {
                const actif = choisis.includes(id);
                return (
                  <button key={id} type="button" aria-pressed={actif} onClick={() => basculer(id)}
                    className={cn("flex items-center gap-2.5 text-left px-3 py-3 rounded-2xl text-sm border transition-colors min-h-[3.25rem]",
                      actif ? "border-primary bg-primary-50 text-primary font-semibold" : "border-gray-200 bg-white text-dark hover:border-primary/40")}>
                    <Icone size={22} weight="duotone" className="flex-shrink-0" aria-hidden /> {label}
                  </button>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </Question>
  );
}

function EcranPhotos({ donnees, modifier, erreurs, onOccupe }: EcranProps) {
  const t = useTranslations("assistantHote");
  const nombre = donnees.images?.length ?? 0;
  const enregistrer = useCallback((images: string[]) => {
    if (images.join() !== (donnees.images ?? []).join()) modifier({ images, image_url: images[0] ?? "" });
  }, [donnees.images, modifier]);
  return (
    <Question cle="photos">
      <ul className="grid gap-2 mb-5 text-sm text-gray-600">
        <li className="flex items-start gap-2"><Sun size={18} className="text-primary flex-shrink-0" aria-hidden /> {t("photos.conseilJour")}</li>
        <li className="flex items-start gap-2"><Camera size={18} className="text-primary flex-shrink-0" aria-hidden /> {t("photos.conseilPieces")}</li>
      </ul>
      <PhotoUploader value={donnees.images ?? []} onChange={enregistrer} onBusyChange={onOccupe} fichiersDuBrouillon
        error={erreurs.images?.[0] ?? erreurs.image_url?.[0]} />
      <p className={cn("text-sm font-semibold mt-3", nombre >= MIN_PHOTOS ? "text-primary" : "text-dark")}>
        {t("photos.compteur", { nombre, min: MIN_PHOTOS })}
      </p>
    </Question>
  );
}

function EcranTitre({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("assistantHote");
  const titre = donnees.name ?? "";
  return (
    <Question cle="titre">
      <label className="sr-only" htmlFor="a-titre">{t("titre.titre")}</label>
      <textarea id="a-titre" rows={2} className={cn(champClass, "resize-none font-heading font-semibold text-lg")} value={titre}
        onChange={(e) => modifier({ name: e.target.value.replace(/\n/g, " ") })} placeholder={t("titre.exemple")} />
      <Compteur valeur={titre.length} max={MAX_TITRE} />
      <Erreur messages={erreurs.name} />
    </Question>
  );
}

function EcranDescription({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("assistantHote");
  const description = donnees.description ?? "";
  return (
    <Question cle="description">
      <label className="sr-only" htmlFor="a-description">{t("description.titre")}</label>
      <textarea id="a-description" rows={8} className={cn(champClass, "resize-y")} value={description}
        onChange={(e) => modifier({ description: e.target.value })} placeholder={t("description.exemple")} />
      <Compteur valeur={description.length} max={MAX_DESCRIPTION} />
      {description.trim().length > 0 && description.trim().length < MIN_DESCRIPTION && (
        <p className="text-sm text-gray-500">{t("description.encore", { nombre: MIN_DESCRIPTION - description.trim().length })}</p>
      )}
      <Erreur messages={erreurs.description} />
    </Question>
  );
}

export const ECRANS: Partial<Record<CleEtape, ComponentType<EcranProps>>> = {
  type: EcranType, espace: EcranEspace, adresse: EcranAdresse, position: EcranPosition, capacite: EcranCapacite,
  equipements: EcranEquipements, photos: EcranPhotos, titre: EcranTitre, description: EcranDescription,
  prix: EcranPrix, regles: EcranRegles, accueil: EcranAccueil, securite: EcranSecurite, telephone: EcranTelephone,
  identite: EcranIdentite, versement: EcranVersement, contrat: EcranContrat, recapitulatif: EcranRecapitulatif,
};
