"use client";

import { useCallback, useEffect, type ComponentType } from "react";
import { useTranslations } from "next-intl";
import { Camera, Check, Plus, Sun, Trash2, type LucideIcon } from "lucide-react";
import { ICONES_TYPES, TYPES_LOGEMENT } from "@/components/hebergement/TypeLogement";
import { useConfigPaiement } from "@/features/paiements";
import { ChoixPosition, type PointCarte } from "@/features/carte";
import Stepper from "@/components/ui/Stepper";
import { useFormat } from "@/lib/format";
import { quartiersDe, VILLES } from "@/lib/quartiers";
import { cn } from "@/lib/utils";
import { useEquipements } from "../AmenityBadge";
import { estEtablissement, type DonneesAnnonce } from "../brouillons";
import PhotoUploader from "../PhotoUploader";
import FraisMenageType from "../FraisMenageType";
import { EcranAccueil, EcranContrat, EcranIdentite, EcranPrix, EcranRecapitulatif, EcranRegles, EcranSecurite, EcranTelephone, EcranVersement } from "./EcransFin";
import { MAX_DESCRIPTION, MAX_TITRE, MIN_DESCRIPTION, MIN_PHOTOS, typeComplet, type CleEtape, type Conditions } from "./etapes";

export interface EcranProps {
  donnees: DonneesAnnonce;
  modifier: (champs: DonneesAnnonce) => void;
  erreurs: Record<string, string[]>;
  /** Photos being sent: the host waits before going on */
  onOccupe: (occupe: boolean) => void;
  conditions?: Conditions;
}

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

/** Big choice with its pictogram, one per option: the question is answered with one touch. */
function CarteChoix({ picto: Picto, titre, texte, note, choisi, onChoisir }: {
  picto: LucideIcon; titre: string; texte: string; note?: string; choisi: boolean; onChoisir: () => void;
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
      <span className={cn("flex items-center justify-center h-20 sm:h-24 rounded-2xl transition-colors duration-200",
        choisi ? "bg-primary text-light" : "bg-light-muted text-primary group-hover:bg-primary-50")}>
        <Picto size={34} strokeWidth={1.5} aria-hidden className="transition-transform duration-300 motion-safe:group-hover:scale-110" />
      </span>
      <span className="block px-2 pt-2.5 pb-2">
        <span className="block font-heading font-bold text-dark text-sm sm:text-base">{titre}</span>
        <span className="block text-xs text-gray-500 mt-0.5 leading-snug">{texte}</span>
        {note && <span className="block text-xs font-semibold text-primary mt-1.5">{note}</span>}
      </span>
      {choisi && (
        <span className="absolute top-3.5 right-3.5 w-7 h-7 rounded-full bg-white text-primary flex items-center justify-center shadow">
          <Check size={16} aria-hidden />
        </span>
      )}
    </button>
  );
}

function EcranType({ donnees, modifier }: EcranProps) {
  const { TYPE_LABELS, formatPrice } = useFormat();
  // Cleaning fee of each type (Kwa-Ba scale), seen before choosing
  const menage = useConfigPaiement().data?.frais_menage;
  const t = useTranslations("assistantHote");
  const tAnnonce = useTranslations("annonce");
  return (
    <Question cle="type">
      <div role="radiogroup" aria-label={t("type.titre")} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {TYPES_LOGEMENT.map((type) => (
          <CarteChoix key={type} picto={ICONES_TYPES[type]} titre={TYPE_LABELS[type]} texte={tAnnonce(`types.${type}`)}
            note={menage?.[type] == null ? undefined
              : menage[type] > 0 ? tAnnonce("menageCarte", { montant: formatPrice(menage[type]) }) : tAnnonce("menageCarteZero")}
            choisi={donnees.type === type}
            // A studio has no separate bedroom
            onChoisir={() => modifier(type === "studio" && donnees.chambres == null ? { type, chambres: 0 } : { type })} />
        ))}
      </div>
      <FraisMenageType type={donnees.type} className="mt-4" />
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
            {VILLES.map(({ nom: ville }) => (
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
          <datalist id="a-quartiers">{quartiersDe(donnees.city ?? "").map((q) => <option key={q} value={q} />)}</datalist>
          <Erreur messages={erreurs.location} />
        </div>
        <div>
          <label className={libelleClass} htmlFor="a-repere">{t("pointRepere")}</label>
          <input id="a-repere" className={champClass} value={donnees.point_repere ?? ""} maxLength={200}
            onChange={(e) => modifier({ point_repere: e.target.value })} placeholder={t("pointRepereExemple")} />
          <p className="text-xs text-gray-500 mt-1.5">{t("pointRepereAide")}</p>
          <Erreur messages={erreurs.point_repere} />
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
  const lits = (donnees.lits_doubles ?? 0) + (donnees.lits_simples ?? 0) + (donnees.canapes_lits ?? 0);
  // The counters show a value from the start: it is saved too, so "Next" is never greyed out by an untouched counter
  const manquants = donnees.max_guests == null || donnees.chambres == null || donnees.salles_de_bain == null;
  useEffect(() => {
    if (manquants) {
      modifier({
        max_guests: donnees.max_guests ?? 2, chambres: donnees.chambres ?? (donnees.type === "studio" ? 0 : 1),
        salles_de_bain: donnees.salles_de_bain ?? 1,
      });
    }
  }, [manquants]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Question cle="capacite">
      <Stepper className={ligne} label={t("voyageursMax")} value={donnees.max_guests ?? 2} min={1} max={20}
        onChange={(n) => modifier({ max_guests: n })} />
      <Stepper className={ligne} label={t("chambres")} value={donnees.chambres ?? 1} min={0} max={50}
        onChange={(n) => modifier({ chambres: n })} />
      <p className="text-xs text-gray-500 pt-1.5">{t("chambresAide")}</p>
      <Stepper className={ligne} label={t("sallesDeBain")} value={donnees.salles_de_bain ?? 1} min={1} max={50}
        onChange={(n) => modifier({ salles_de_bain: n })} />
      <Stepper className={ligne} label={t("litsDoubles")} value={donnees.lits_doubles ?? 0} min={0} max={50}
        onChange={(n) => modifier({ lits_doubles: n })} />
      <Stepper className={ligne} label={t("litsSimples")} value={donnees.lits_simples ?? 0} min={0} max={50}
        onChange={(n) => modifier({ lits_simples: n })} />
      <Stepper className={ligne} label={t("canapesLits")} value={donnees.canapes_lits ?? 0} min={0} max={50}
        onChange={(n) => modifier({ canapes_lits: n })} />
      {/* Says why "Next" waits, instead of a greyed-out button without explanation */}
      {lits === 0 && <p role="status" className="text-sm text-secondary font-semibold mt-3">{t("litsRequis")}</p>}
      <Erreur messages={erreurs.lits ?? erreurs.max_guests ?? erreurs.salles_de_bain} />
    </Question>
  );
}

type TypeChambre = NonNullable<DonneesAnnonce["types_chambres"]>[number];
const NOUVEAU_TYPE: TypeChambre = { nom: "", prix_nuit: 0, quantite: 1, capacite: 2 };

/** The listing's price and capacity follow its room types: the cheapest price ("from"), the largest room. */
function avecTypes(types: TypeChambre[]): DonneesAnnonce {
  const complets = types.filter(typeComplet);
  return {
    types_chambres: types,
    ...(complets.length ? {
      price_per_night: Math.min(...complets.map((u) => u.prix_nuit)),
      max_guests: Math.min(20, Math.max(...complets.map((u) => u.capacite))),
    } : {}),
  };
}

/** A hotel, an aparthotel or a guesthouse: its room types and how many of each, instead of the beds of a house. */
function EcranChambres({ donnees, modifier, erreurs }: EcranProps) {
  const t = useTranslations("assistantHote.chambres");
  const { formatPrice } = useFormat();
  const types = donnees.types_chambres ?? [];
  useEffect(() => {
    if (!donnees.types_chambres?.length) modifier(avecTypes([NOUVEAU_TYPE]));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const changer = (i: number, champs: Partial<TypeChambre>) => modifier(avecTypes(types.map((u, j) => (j === i ? { ...u, ...champs } : u))));
  const nombre = (valeur: string) => (valeur ? Number(valeur) : 0);
  const total = types.reduce((somme, u) => somme + (u.quantite || 0), 0);
  const complets = types.filter(typeComplet);
  return (
    <Question cle="chambres">
      <div className="space-y-4">
        {types.map((u, i) => (
          <fieldset key={i} className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
            <legend className="sr-only">{t("typeNumero", { numero: i + 1 })}</legend>
            <div className="flex items-start gap-2">
              <label className="flex-1">
                <span className={libelleClass}>{t("nom")}</span>
                <input className={champClass} value={u.nom} maxLength={120} placeholder={t("nomExemple")}
                  onChange={(e) => changer(i, { nom: e.target.value })} />
              </label>
              {types.length > 1 && (
                <button type="button" onClick={() => modifier(avecTypes(types.filter((_, j) => j !== i)))} aria-label={t("retirer")}
                  className="mt-7 w-11 h-11 flex-shrink-0 rounded-full text-red-600 hover:bg-red-50 flex items-center justify-center">
                  <Trash2 size={18} aria-hidden />
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label>
                <span className={libelleClass}>{t("prix")}</span>
                <input className={champClass} type="number" inputMode="numeric" min={1} placeholder="25000"
                  value={u.prix_nuit || ""} onChange={(e) => changer(i, { prix_nuit: nombre(e.target.value) })} />
              </label>
              <label>
                <span className={libelleClass}>{t("quantite")}</span>
                <input className={champClass} type="number" inputMode="numeric" min={1} max={500}
                  value={u.quantite || ""} onChange={(e) => changer(i, { quantite: nombre(e.target.value) })} />
              </label>
              <label>
                <span className={libelleClass}>{t("capacite")}</span>
                <input className={champClass} type="number" inputMode="numeric" min={1} max={50}
                  value={u.capacite || ""} onChange={(e) => changer(i, { capacite: nombre(e.target.value) })} />
              </label>
            </div>
          </fieldset>
        ))}
        <button type="button" onClick={() => modifier(avecTypes([...types, NOUVEAU_TYPE]))} disabled={types.length >= 30}
          className="w-full flex items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-300 py-3.5 text-sm font-semibold text-primary hover:border-primary/50 disabled:opacity-50">
          <Plus size={18} aria-hidden /> {t("ajouter")}
        </button>
        {complets.length > 0 && (
          <p className="text-sm font-semibold text-primary">
            {t("resume", { total, prix: formatPrice(Math.min(...complets.map((u) => u.prix_nuit))) })}
          </p>
        )}
        <p className="text-xs text-gray-500">{t("aide")}</p>
        <Erreur messages={erreurs.types_chambres} />
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
  const sansPiece = (donnees.images ?? []).filter((url) => !donnees.legendes_photos?.[url]).length;
  return (
    <Question cle="photos">
      <ul className="grid gap-2 mb-5 text-sm text-gray-600">
        <li className="flex items-start gap-2"><Sun size={18} className="text-primary flex-shrink-0" aria-hidden /> {t("photos.conseilJour")}</li>
        <li className="flex items-start gap-2"><Camera size={18} className="text-primary flex-shrink-0" aria-hidden /> {t("photos.conseilPieces")}</li>
      </ul>
      <PhotoUploader value={donnees.images ?? []} onChange={enregistrer} onBusyChange={onOccupe} fichiersDuBrouillon
        error={erreurs.images?.[0] ?? erreurs.image_url?.[0] ?? erreurs.legendes_photos?.[0]}
        legendes={donnees.legendes_photos ?? {}} chambres={donnees.chambres} sallesDeBain={donnees.salles_de_bain}
        etablissement={estEtablissement(donnees.type)}
        onLegende={(url, piece) => modifier({ legendes_photos: { ...donnees.legendes_photos, [url]: piece } })} />
      <p className={cn("text-sm font-semibold mt-3", nombre >= MIN_PHOTOS ? "text-primary" : "text-dark")}>
        {t("photos.compteur", { nombre, min: MIN_PHOTOS })}
      </p>
      {/* Says why "Next" waits */}
      {sansPiece > 0 && <p role="status" className="text-sm text-secondary font-semibold mt-1">{t("photos.pieces", { nombre: sansPiece })}</p>}
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
  type: EcranType, adresse: EcranAdresse, chambres: EcranChambres, position: EcranPosition, capacite: EcranCapacite,
  equipements: EcranEquipements, photos: EcranPhotos, titre: EcranTitre, description: EcranDescription,
  prix: EcranPrix, regles: EcranRegles, accueil: EcranAccueil, securite: EcranSecurite, telephone: EcranTelephone,
  identite: EcranIdentite, versement: EcranVersement, contrat: EcranContrat, recapitulatif: EcranRecapitulatif,
};
