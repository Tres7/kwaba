"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import Categories from "@/features/locations/admin/Categories";
import Lieux from "@/features/locations/admin/Lieux";
import Loueurs from "@/features/locations/admin/Loueurs";
import Regles from "@/features/locations/admin/Regles";
import Suivi from "@/features/locations/admin/Suivi";

const ONGLETS = [
  { id: "suivi", label: "Locations", Composant: Suivi },
  { id: "categories", label: "Véhicules", Composant: Categories },
  { id: "lieux", label: "Lieux de remise", Composant: Lieux },
  { id: "loueurs", label: "Propriétaires", Composant: Loueurs },
  { id: "regles", label: "Règles", Composant: Regles },
];

function Location() {
  const router = useRouter();
  const pathname = usePathname();
  const onglet = useSearchParams().get("onglet") ?? "suivi";
  const { Composant } = ONGLETS.find((o) => o.id === onglet) ?? ONGLETS[0];
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Location de voiture</h1>
        <p className="text-muted text-sm mt-1">Locations et chauffeurs à attribuer, véhicules des propriétaires, lieux, propriétaires partenaires et règles.</p>
      </div>
      <div role="tablist" className="flex gap-5 overflow-x-auto scrollbar-hide border-b border-gray-200">
        {ONGLETS.map((o) => (
          <button key={o.id} role="tab" aria-selected={onglet === o.id} onClick={() => router.replace(`${pathname}?onglet=${o.id}`)}
            className={cn("relative zone-tactile pb-3 text-sm font-bold whitespace-nowrap border-b-2 transition-colors",
              onglet === o.id ? "text-primary border-primary" : "text-gray-500 border-transparent hover:text-dark")}>
            {o.label}
          </button>
        ))}
      </div>
      <Composant />
    </div>
  );
}

export default function LocationPage() {
  return <Suspense><Location /></Suspense>;
}
