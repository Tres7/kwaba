"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { IControl, Map as CarteGl } from "maplibre-gl";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

// Same camera as the 3D view of openfreemap.org
const RELIEF = { pitch: 60, bearing: 55 };
const A_PLAT = { pitch: 0, bearing: 0 };

/**
 * Tilted view: the buildings rise from zoom 14. Left to the visitor on a phone: the tilted view loads about 3 times more tiles.
 * A map control: it stacks under the zoom buttons, whatever their size. `ouvert`: starts tilted on a large screen.
 */
export default function BoutonRelief({ carte, ouvert = false }: { carte: CarteGl; ouvert?: boolean }) {
  const t = useTranslations("carte");
  const [actif, setActif] = useState(false);
  const [place, setPlace] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const element = document.createElement("div");
    element.className = "maplibregl-ctrl";
    const controle: IControl = { onAdd: () => element, onRemove: () => element.remove() };
    carte.addControl(controle, "top-right");
    setPlace(element);
    return () => { carte.removeControl(controle); };
  }, [carte]);

  useEffect(() => {
    if (!ouvert || !window.matchMedia("(min-width: 1024px)").matches) return;
    setActif(true);
    carte.jumpTo(RELIEF);
  }, [carte, ouvert]);

  const basculer = () => {
    setActif(!actif);
    carte.easeTo({ ...(actif ? A_PLAT : RELIEF), duration: 700 });
  };

  if (!place) return null;

  return createPortal(
    <button
      type="button" onClick={basculer} aria-pressed={actif} aria-label={t("relief")} title={t("relief")}
      className={cn("zone-tactile relative block w-[29px] h-[29px] rounded-xl shadow-md text-[11px] font-bold transition-colors",
        actif ? "!bg-primary text-white" : "!bg-white text-dark hover:!bg-gray-100")}
    >
      3D
    </button>,
    place,
  );
}
