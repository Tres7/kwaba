"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import Contrats from "@/features/contrats/admin/Contrats";
import ModelesContrats from "@/features/contrats/admin/ModelesContrats";
import Factures from "@/features/documents/admin/Factures";
import Societe from "@/features/documents/admin/Societe";

const ONGLETS = [
  { id: "factures", label: "Factures", Composant: Factures },
  { id: "contrats", label: "Contrats", Composant: Contrats },
  { id: "modeles", label: "Modèles de contrat", Composant: ModelesContrats },
  { id: "societe", label: "Informations société", Composant: Societe },
];

function Documents() {
  const router = useRouter();
  const pathname = usePathname();
  const onglet = useSearchParams().get("onglet") ?? "factures";
  const { Composant } = ONGLETS.find((o) => o.id === onglet) ?? ONGLETS[0];
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Documents</h1>
        <p className="text-muted text-sm mt-1">Factures, contrats signés électroniquement et informations légales imprimées sur tous les documents.</p>
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

export default function DocumentsPage() {
  return <Suspense><Documents /></Suspense>;
}
