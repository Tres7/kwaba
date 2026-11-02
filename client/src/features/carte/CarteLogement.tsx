"use client";

import { useEffect } from "react";
import type { Hebergement } from "@/types/api/models";
import BoutonRelief from "./BoutonRelief";
import { zoneCirculaire } from "./geometrie";
import { COUCHE_RELIEF } from "./style";
import { CadreCarte, useCarte } from "./useCarte";

const ZONE = "zone-logement";
const VERT_KWABA = "#0E4D47";

/** Listing page: the zone of the listing, never its exact position (the API does not give it). */
export default function CarteLogement({ position }: { position: NonNullable<Hebergement["position"]> }) {
  // Two fingers on a phone, Ctrl + scroll on a computer: the page must keep scrolling over the map
  const { conteneur, carte, panne } = useCarte({ center: [position.lng, position.lat], zoom: 14, cooperativeGestures: true });

  useEffect(() => {
    if (!carte || carte.getSource(ZONE)) return;
    carte.addSource(ZONE, { type: "geojson", data: zoneCirculaire(position, position.rayon_m) });
    // On the ground: the buildings rise above the zone
    const dessous = carte.getLayer(COUCHE_RELIEF) ? COUCHE_RELIEF : undefined;
    carte.addLayer({ id: ZONE, type: "fill", source: ZONE, paint: { "fill-color": VERT_KWABA, "fill-opacity": 0.14 } }, dessous);
    carte.addLayer({ id: `${ZONE}-bord`, type: "line", source: ZONE, paint: { "line-color": VERT_KWABA, "line-width": 2 } }, dessous);
  }, [carte, position]);

  return (
    <CadreCarte conteneur={conteneur} charge={!!carte} panne={panne}>
      {carte && !panne && <BoutonRelief carte={carte} ouvert />}
    </CadreCarte>
  );
}
