"use client";

import { useEffect, useRef, useState } from "react";
import { Marker, type MapMouseEvent } from "maplibre-gl";
import { Crosshair, LocateFixed } from "lucide-react";
import { useTranslations } from "next-intl";
import { CENTRE_LOME, arrondi, centreDeVille, type PointCarte } from "./geometrie";
import { CadreCarte, useCarte } from "./useCarte";

const VERT_KWABA = "#0E4D47";
const ZOOM_PRECIS = 17;
const boutonClass = "inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-dark hover:border-primary/40 disabled:opacity-60";

/** Host form: the exact position of the listing, placed on the map. `ville` moves the map while no pin is placed. */
export default function ChoixPosition({ valeur, onChange, ville }: {
  valeur: PointCarte | null;
  onChange: (position: PointCarte) => void;
  ville: string;
}) {
  const t = useTranslations("carte.choix");
  const depart = valeur ?? centreDeVille(ville) ?? CENTRE_LOME;
  const { conteneur, carte, panne } = useCarte({ center: [depart.lng, depart.lat], zoom: valeur ? 16 : 12 });
  const repere = useRef<Marker | null>(null);
  const [localisation, setLocalisation] = useState<"" | "en_cours" | "refus">("");

  useEffect(() => {
    if (!carte || !valeur) return;
    if (!repere.current) {
      const marqueur = new Marker({ color: VERT_KWABA, draggable: true }).setLngLat([valeur.lng, valeur.lat]).addTo(carte);
      marqueur.on("dragend", () => onChange(arrondi(marqueur.getLngLat())));
      repere.current = marqueur;
    }
    repere.current.setLngLat([valeur.lng, valeur.lat]);
  }, [carte, valeur, onChange]);

  useEffect(() => {
    if (!carte) return;
    const placer = (e: MapMouseEvent) => onChange(arrondi(e.lngLat));
    carte.on("click", placer);
    return () => { carte.off("click", placer); };
  }, [carte, onChange]);

  const sansRepere = !valeur;
  useEffect(() => {
    const centre = centreDeVille(ville);
    if (carte && centre && sansRepere) carte.jumpTo({ center: [centre.lng, centre.lat], zoom: 12 });
  }, [carte, ville, sansRepere]);

  const localiser = () => {
    if (!navigator.geolocation) {
      setLocalisation("refus");
      return;
    }
    setLocalisation("en_cours");
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      const position = arrondi({ lat: coords.latitude, lng: coords.longitude });
      setLocalisation("");
      onChange(position);
      carte?.flyTo({ center: [position.lng, position.lat], zoom: ZOOM_PRECIS });
    }, () => setLocalisation("refus"), { enableHighAccuracy: true, timeout: 15_000 });
  };

  return (
    <div>
      <div className="h-72 sm:h-80 rounded-xl overflow-hidden border border-gray-200">
        <CadreCarte conteneur={conteneur} charge={!!carte} panne={panne} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={localiser} disabled={!carte || localisation === "en_cours"} className={boutonClass}>
          <LocateFixed size={16} aria-hidden /> {localisation === "en_cours" ? t("recherche") : t("maPosition")}
        </button>
        {/* Without a pointer: move the map with the arrow keys, then drop the pin in its centre */}
        <button type="button" onClick={() => carte && onChange(arrondi(carte.getCenter()))} disabled={!carte} className={boutonClass}>
          <Crosshair size={16} aria-hidden /> {t("placerAuCentre")}
        </button>
      </div>
      {localisation === "refus" && <p role="alert" className="text-xs text-red-600 mt-1.5">{t("refus")}</p>}
      <p className="text-xs text-gray-500 mt-2">{valeur ? t("placee") : t("aide")} {t("prive")}</p>
    </div>
  );
}
