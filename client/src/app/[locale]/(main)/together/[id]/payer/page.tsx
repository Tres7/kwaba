"use client";

import { Suspense } from "react";
import PaiementGroupe from "@/features/voyages/PaiementGroupe";

export default function PaiementGroupePage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] bg-light" />}>
      <PaiementGroupe />
    </Suspense>
  );
}
