"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/** Data saver turned on in the browser: the wizard works just as well without its images. */
function useEconomieDonnees() {
  const [economie, setEconomie] = useState(false);
  useEffect(() => {
    const connexion = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
    setEconomie(!!connexion?.saveData);
  }, []);
  return economie;
}

/**
 * 3D miniature of the screen, on the sand background. The images have a slightly different cream around the object:
 * the edge fades out so that no square shows against the panel.
 */
export default function Decor({ src, suivant, grand }: { src: string; suivant?: string; grand?: boolean }) {
  const economie = useEconomieDonnees();

  // The next image is ready when the host presses Next, even on a slow connection
  useEffect(() => {
    if (suivant && !economie) new Image().src = suivant;
  }, [suivant, economie]);

  if (economie) return null;
  return (
    <div className={cn("assistant-flotte relative h-full aspect-square", grand ? "max-w-[34rem] lg:max-w-[38rem]" : "max-w-[30rem]")}>
      <img
        key={src} src={src} alt="" width={800} height={800} fetchPriority="high"
        className="assistant-visuel h-full w-full object-contain"
        style={{
          maskImage: "radial-gradient(closest-side, #000 76%, transparent 100%)",
          WebkitMaskImage: "radial-gradient(closest-side, #000 76%, transparent 100%)",
        }}
      />
    </div>
  );
}
