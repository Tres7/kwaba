import {
  BabyIcon, BarbellIcon, BathtubIcon, BroomIcon, BugIcon, CarIcon, ChefHatIcon, CheckCircleIcon, CigaretteIcon, CigaretteSlashIcon,
  ConfettiIcon, CookingPotIcon, DeskIcon, DropIcon, FanIcon, FireExtinguisherIcon, FlameIcon, LightningIcon, PawPrintIcon, PlantIcon,
  SecurityCameraIcon, ShieldCheckIcon, ShowerIcon, SnowflakeIcon, SolarPanelIcon, SwimmingPoolIcon, TelevisionSimpleIcon,
  ThermometerColdIcon, TowelIcon, TShirtIcon, UmbrellaIcon, VaultIcon, WashingMachineIcon, WavesIcon, WheelchairIcon, WifiHighIcon,
  type Icon,
} from "@phosphor-icons/react";
import { useLocale } from "next-intl";
import { cn } from "@/lib/utils";

type Equipement = [id: string, fr: string, en: string, Icone: Icon];

/** Amenities by category, in the order of the form and of the listing page (same list as the API: hebergements/serializers.py). */
const CATEGORIES: { id: string; fr: string; en: string; equipements: Equipement[] }[] = [
  { id: "essentiels", fr: "Essentiels", en: "Essentials", equipements: [
    ["wifi", "WiFi", "Wi-Fi", WifiHighIcon],
    ["clim", "Climatisation", "Air conditioning", SnowflakeIcon],
    ["ventilateur", "Ventilateur", "Fan", FanIcon],
    ["eau_chaude", "Eau chaude", "Hot water", ShowerIcon],
    ["moustiquaire", "Moustiquaires", "Mosquito nets", BugIcon],
    ["tv", "Télévision", "TV", TelevisionSimpleIcon],
    ["fer_repasser", "Fer à repasser", "Iron", TShirtIcon],
    ["lave_linge", "Lave-linge", "Washing machine", WashingMachineIcon],
    ["espace_travail", "Espace de travail", "Workspace", DeskIcon],
  ] },
  { id: "energie", fr: "Électricité et eau", en: "Power and water", equipements: [
    ["groupe_electrogene", "Groupe électrogène", "Generator", LightningIcon],
    ["solaire", "Panneaux solaires ou onduleur", "Solar panels or inverter", SolarPanelIcon],
    ["reserve_eau", "Réserve d'eau (citerne, forage)", "Water tank or borehole", DropIcon],
  ] },
  { id: "cuisine", fr: "Cuisine", en: "Kitchen", equipements: [
    ["cuisine", "Cuisine", "Kitchen", CookingPotIcon],
    ["refrigerateur", "Réfrigérateur", "Fridge", ThermometerColdIcon],
    ["barbecue", "Barbecue", "Barbecue", FlameIcon],
  ] },
  { id: "exterieur", fr: "Extérieur et détente", en: "Outdoors and leisure", equipements: [
    ["piscine", "Piscine", "Swimming pool", SwimmingPoolIcon],
    ["jardin", "Jardin", "Garden", PlantIcon],
    ["terrasse", "Terrasse ou balcon", "Terrace or balcony", UmbrellaIcon],
    ["acces_plage", "Accès à la plage", "Beach access", WavesIcon],
    ["gym", "Salle de sport", "Gym", BarbellIcon],
    ["spa", "Spa", "Spa", BathtubIcon],
  ] },
  { id: "securite", fr: "Sécurité", en: "Safety", equipements: [
    ["gardien", "Gardien", "Guard", ShieldCheckIcon],
    ["videosurveillance", "Vidéosurveillance", "CCTV", SecurityCameraIcon],
    ["parking", "Parking", "Parking", CarIcon],
    ["coffre_fort", "Coffre-fort", "Safe", VaultIcon],
    ["extincteur", "Extincteur", "Fire extinguisher", FireExtinguisherIcon],
  ] },
  { id: "services", fr: "Services", en: "Services", equipements: [
    ["menage", "Ménage inclus", "Cleaning included", BroomIcon],
    ["linge", "Draps et serviettes fournis", "Linen and towels provided", TowelIcon],
    ["cuisinier", "Cuisinier sur demande", "Cook on request", ChefHatIcon],
    ["lit_bebe", "Lit bébé", "Baby cot", BabyIcon],
    ["plain_pied", "Accès de plain-pied", "Step-free access", WheelchairIcon],
  ] },
];

/**
 * House rules, stored in the same list as the amenities: one value of each pair at most,
 * none when the host did not say (the oldest listings).
 */
const REGLES_MAISON: { id: string; fr: string; en: string; oui: Equipement; non: Equipement }[] = [
  { id: "fumeur", fr: "Fumer", en: "Smoking",
    oui: ["fumeur_autorise", "Fumeur autorisé", "Smoking allowed", CigaretteIcon],
    non: ["non_fumeur", "Non-fumeur", "No smoking", CigaretteSlashIcon] },
  { id: "animaux", fr: "Animaux", en: "Pets",
    oui: ["animaux_acceptes", "Animaux acceptés", "Pets allowed", PawPrintIcon],
    non: ["animaux_interdits", "Animaux non acceptés", "No pets", PawPrintIcon] },
  { id: "fetes", fr: "Fêtes et événements", en: "Parties and events",
    oui: ["fetes_autorisees", "Fêtes autorisées", "Parties allowed", ConfettiIcon],
    non: ["fetes_interdites", "Pas de fêtes", "No parties", ConfettiIcon] },
];

/** Most searched amenities: always shown in the search filters, the others behind « more ». */
export const EQUIPEMENTS_PRINCIPAUX = ["wifi", "clim", "ventilateur", "groupe_electrogene", "eau_chaude", "piscine", "parking", "cuisine", "gardien"];

function creerEquipements(langue: "fr" | "en") {
  const avecLibelle = ([id, fr, en, Icone]: Equipement) => ({ id, Icone, label: langue === "en" ? en : fr });
  return {
    CATEGORIES_EQUIPEMENTS: CATEGORIES.map((c) => ({ id: c.id, label: c[langue], equipements: c.equipements.map(avecLibelle) })),
    REGLES: REGLES_MAISON.map((r) => ({ id: r.id, label: r[langue], oui: avecLibelle(r.oui), non: avecLibelle(r.non) })),
    /** Amenities and house rules. */
    AMENITIES: Object.fromEntries(
      [...CATEGORIES.flatMap((c) => c.equipements), ...REGLES_MAISON.flatMap((r) => [r.oui, r.non])]
        .map(([id, fr, en, Icone]) => [id, { Icone, label: langue === "en" ? en : fr }]),
    ) as Record<string, { label: string; Icone: Icon }>,
  };
}

const EQUIPEMENTS = { fr: creerEquipements("fr"), en: creerEquipements("en") };

export const IDS_EQUIPEMENTS = Object.keys(EQUIPEMENTS.fr.AMENITIES);

/** Amenities and house rules, labelled in the language of the page. */
export function useEquipements() {
  return EQUIPEMENTS[useLocale() === "en" ? "en" : "fr"];
}

const VALEURS_REGLES = new Set(REGLES_MAISON.flatMap((r) => [r.oui[0], r.non[0]]));
export const estRegle = (id: string) => VALEURS_REGLES.has(id);

interface AmenityBadgeProps {
  amenity: string;
}

export default function AmenityBadge({ amenity }: AmenityBadgeProps) {
  const { AMENITIES, REGLES } = useEquipements();
  const { label, Icone } = AMENITIES[amenity] ?? { label: amenity, Icone: CheckCircleIcon };
  // A forbidden house rule: same picture, struck through and muted
  const interdit = REGLES.some((r) => r.non.id === amenity);
  return (
    <div className="flex items-center gap-3 bg-light-muted rounded-xl px-3 py-2.5">
      <span className={cn("relative h-8 w-8 rounded-lg bg-white shadow-sm flex items-center justify-center flex-shrink-0", interdit ? "text-gray-500" : "text-primary")}>
        <Icone size={20} weight="duotone" aria-hidden />
        {interdit && amenity !== "non_fumeur" && <span aria-hidden className="absolute w-6 h-0.5 bg-gray-500 rotate-45 rounded-full" />}
      </span>
      <span className="text-sm text-dark">{label}</span>
    </div>
  );
}
