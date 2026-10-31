"use client";

import { useEffect, useRef, useState } from "react";
import { AttributionControl, Map as CarteGl, NavigationControl, setWorkerUrl, type MapOptions } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapPinOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { STYLE_CARTE, auxCouleursKwaBa } from "./style";

// A separate file in MapLibre 6: webpack publishes it with the site, so the CSP only needs 'self'
setWorkerUrl(new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).href);

// The style is a small file: without it after this long, the map is not coming
const DELAI_STYLE_MS = 15_000;

/**
 * A map of the site. `carte` stays null until its style is received, `panne` if it never is (no WebGL, tiles unreachable).
 * Not the "load" event: it waits for every tile of the view, and one slow tile would hold back the prices, which need none.
 */
export function useCarte(options: Omit<MapOptions, "container" | "style">) {
  const t = useTranslations("carte");
  const conteneur = useRef<HTMLDivElement>(null);
  const [carte, setCarte] = useState<CarteGl | null>(null);
  const [panne, setPanne] = useState(false);
  // Starting view: later changes go through the map itself
  const depart = useRef({
    ...options,
    locale: {
      "Map.Title": t("titre"),
      "NavigationControl.ZoomIn": t("zoomAvant"),
      "NavigationControl.ZoomOut": t("zoomArriere"),
      "AttributionControl.ToggleAttribution": t("credits"),
      "CooperativeGesturesHandler.WindowsHelpText": t("gesteOrdinateur"),
      "CooperativeGesturesHandler.MacHelpText": t("gesteMac"),
      "CooperativeGesturesHandler.MobileHelpText": t("gesteTelephone"),
    },
  });

  useEffect(() => {
    if (!conteneur.current) return;
    let instance: CarteGl;
    try {
      instance = new CarteGl({
        minZoom: 3, maxZoom: 17, dragRotate: false, pitchWithRotate: false, attributionControl: false,
        ...depart.current, container: conteneur.current,
      });
    } catch {
      setPanne(true);
      return;
    }
    let styleCharge = false;
    const delai = setTimeout(() => { if (!styleCharge) setPanne(true); }, DELAI_STYLE_MS);
    instance.once("style.load", () => {
      styleCharge = true;
      setPanne(false);
      setCarte(instance);
    });
    instance.on("error", () => { if (!styleCharge) setPanne(true); });
    instance.touchZoomRotate.disableRotation();
    instance.addControl(new NavigationControl({ showCompass: false }), "top-right");
    // On the left: required credits, and the Concierge button floats on the right
    instance.addControl(new AttributionControl({ compact: true }), "bottom-left");
    instance.setStyle(STYLE_CARTE, { transformStyle: (_, suivant) => auxCouleursKwaBa(suivant) });
    return () => {
      clearTimeout(delai);
      setCarte(null);
      instance.remove();
    };
  }, []);

  return { conteneur, carte, panne };
}

/** Frame of a map: rounded controls, placeholder while it loads, message if it cannot be shown. */
export function CadreCarte({ conteneur, charge, panne, children }: {
  conteneur: React.Ref<HTMLDivElement>;
  charge: boolean;
  panne: boolean;
  children?: React.ReactNode;
}) {
  const t = useTranslations("carte");
  return (
    <div className="relative w-full h-full [&_.maplibregl-ctrl-group]:!rounded-xl [&_.maplibregl-ctrl-group]:!shadow-md [&_.maplibregl-ctrl-group]:overflow-hidden">
      <div ref={conteneur} className="w-full h-full" />
      {!charge && !panne && <div className="absolute inset-0 skeleton" />}
      {panne && (
        <div role="status" className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-light-muted p-6 text-center">
          <MapPinOff size={26} className="text-muted" aria-hidden />
          <p className="text-sm text-dark">{t("indisponible")}</p>
        </div>
      )}
      {children}
    </div>
  );
}
