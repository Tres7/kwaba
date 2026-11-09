"use client";

import { useState } from "react";
import { PRECISION_MAX_M, type PositionMesuree } from "./position";

const ERREURS: Record<number, string> = {
  1: "Localisation refusée : autorisez-la pour Kwa-Ba dans les réglages du navigateur, puis réessayez.",
  2: "Position introuvable : activez la localisation du téléphone et sortez à découvert.",
  3: "Le GPS met trop de temps : sortez à découvert et réessayez.",
};

/** The phone's GPS in high accuracy, for the position of a listing: a reading less accurate than PRECISION_MAX_M
 * (indoors, GPS not fixed yet) is refused with an explanation. */
export function useGps(onMesure: (position: PositionMesuree) => void) {
  const [recherche, setRecherche] = useState(false);
  const [erreur, setErreur] = useState("");

  const relever = () => {
    if (!("geolocation" in navigator)) {
      setErreur("Ce navigateur ne donne pas la position : ouvrez l'espace agent dans Chrome ou Safari.");
      return;
    }
    setRecherche(true);
    setErreur("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setRecherche(false);
        if (coords.accuracy > PRECISION_MAX_M) {
          setErreur(`Position trop imprécise (± ${Math.round(coords.accuracy)} m) : sortez à découvert et reprenez-la.`);
          return;
        }
        onMesure({ latitude: coords.latitude, longitude: coords.longitude, precision: coords.accuracy });
      },
      (err) => {
        setRecherche(false);
        setErreur(ERREURS[err.code] ?? "Position indisponible : réessayez.");
      },
      { enableHighAccuracy: true, timeout: 20_000, maximumAge: 0 },
    );
  };

  return { relever, recherche, erreur };
}
