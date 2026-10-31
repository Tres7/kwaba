"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { DonsAdmin, OrganisationsAdmin, ReversementsAdmin } from "@/features/give";

const ONGLETS = [
  { id: "ong", label: "ONG et projets", Composant: OrganisationsAdmin },
  { id: "reversements", label: "Reversements", Composant: ReversementsAdmin },
  { id: "dons", label: "Dons", Composant: DonsAdmin },
];

function Give() {
  const router = useRouter();
  const pathname = usePathname();
  const onglet = useSearchParams().get("onglet") ?? "ong";
  const { Composant } = ONGLETS.find((o) => o.id === onglet) ?? ONGLETS[0];
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Kwa-Ba Give</h1>
        <p className="text-muted text-sm mt-1">ONG partenaires et leurs projets, reversements mensuels avec preuve, dons reçus.</p>
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

export default function GivePage() {
  return <Suspense><Give /></Suspense>;
}
