import { BarbellIcon, BathtubIcon, CarIcon, CheckCircleIcon, CookingPotIcon, PlantIcon, SnowflakeIcon, SwimmingPoolIcon, WifiHighIcon, type Icon } from "@phosphor-icons/react";
import { selon } from "@/lib/utils";

const EQUIPEMENTS: [string, string, string, Icon][] = [
  ["piscine", "Piscine", "Swimming pool", SwimmingPoolIcon],
  ["wifi", "WiFi", "Wi-Fi", WifiHighIcon],
  ["clim", "Climatisation", "Air conditioning", SnowflakeIcon],
  ["parking", "Parking", "Parking", CarIcon],
  ["cuisine", "Cuisine", "Kitchen", CookingPotIcon],
  ["jardin", "Jardin", "Garden", PlantIcon],
  ["gym", "Salle de sport", "Gym", BarbellIcon],
  ["spa", "Spa", "Spa", BathtubIcon],
];

/** Amenities, labelled in the current language. */
export const AMENITIES: Record<string, { label: string; Icone: Icon }> = Object.fromEntries(
  EQUIPEMENTS.map(([id, fr, en, Icone]) => [id, { Icone, get label() { return selon({ fr, en }); } }]),
);

interface AmenityBadgeProps {
  amenity: string;
}

export default function AmenityBadge({ amenity }: AmenityBadgeProps) {
  const { label, Icone } = AMENITIES[amenity] ?? { label: amenity, Icone: CheckCircleIcon };
  return (
    <div className="flex items-center gap-3 bg-light-muted rounded-xl px-3 py-2.5">
      <span className="h-8 w-8 rounded-lg bg-white text-primary shadow-sm flex items-center justify-center flex-shrink-0">
        <Icone size={20} weight="duotone" aria-hidden />
      </span>
      <span className="text-sm text-dark">{label}</span>
    </div>
  );
}
