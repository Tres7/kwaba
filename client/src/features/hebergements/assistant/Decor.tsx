"use client";

import { useId } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/** Colour of each phase: the same on the welcome screen and on every screen of the phase. */
const TEINTES = {
  0: "bg-primary text-light",
  1: "bg-primary text-light",
  2: "bg-accent text-dark",
  3: "bg-primary-800 text-accent",
} as const;

export type Phase = keyof typeof TEINTES;

/** Pictogram on a tile of its phase colour. Its size comes from `className`. */
export function Tuile({ picto: Picto, phase, className }: { picto: LucideIcon; phase: Phase; className?: string }) {
  return (
    <span className={cn("flex items-center justify-center rounded-[28%] shadow-[0_24px_48px_-24px_rgba(14,77,71,0.55)]", TEINTES[phase], className)}>
      <Picto strokeWidth={1.5} className="h-1/2 w-1/2" aria-hidden />
    </span>
  );
}

/** The tile, floating, on a tilted plate that gives it depth. */
export function TuileFlottante({ picto, phase, className }: { picto: LucideIcon; phase: Phase; className?: string }) {
  return (
    <div className={cn("assistant-flotte relative aspect-square", className)}>
      <span aria-hidden className="absolute inset-0 rounded-[28%] bg-primary-100 translate-x-[7%] translate-y-[7%] rotate-6" />
      <Tuile picto={picto} phase={phase} className="assistant-visuel absolute inset-0" />
    </div>
  );
}

/** Diamonds and dots in the brand green, faint, fading out towards the middle: drawn in the page, nothing to download. */
export function Motif() {
  const id = `motif-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const masque = "radial-gradient(circle, transparent 15%, #000 75%)";
  return (
    <svg aria-hidden className="absolute inset-0 h-full w-full text-primary/[0.09]" style={{ maskImage: masque, WebkitMaskImage: masque }}>
      <defs>
        <pattern id={id} width="44" height="44" patternUnits="userSpaceOnUse">
          <path d="M22 6 38 22 22 38 6 22Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="22" cy="22" r="2.5" fill="currentColor" />
          <circle cx="0" cy="0" r="1.75" fill="currentColor" />
          <circle cx="44" cy="0" r="1.75" fill="currentColor" />
          <circle cx="0" cy="44" r="1.75" fill="currentColor" />
          <circle cx="44" cy="44" r="1.75" fill="currentColor" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}

/** Side panel of a screen: the pattern and, above it, the pictogram of the screen. */
export default function Decor({ picto, phase, grand }: { picto: LucideIcon; phase: Phase; grand?: boolean }) {
  return (
    <>
      <Motif />
      <TuileFlottante picto={picto} phase={phase} className={cn("h-[58%] lg:h-auto", grand ? "lg:w-80" : "lg:w-64")} />
    </>
  );
}
