"use client";

import { useParams, useSearchParams } from "next/navigation";
import { PayerPourAutrui } from "@/features/paiement-tiers";
import { demarrerPaiementGroupe, lireApercuGroupe } from "./api";

/** A member pays the booking shared with the trip, in the booker's place: /together/<trip>/payer?r=<share>. */
export default function PaiementGroupe() {
  const { id } = useParams<{ id: string }>();
  // The share is in the query string: the analytics measure the address without it (lib/mesure-audience.ts)
  const partage = Number(useSearchParams().get("r"));
  return (
    <PayerPourAutrui
      cle={["voyages", id, "paiement", partage]}
      charger={() => lireApercuGroupe(id, partage)}
      demarrer={(moyen) => demarrerPaiementGroupe(id, partage, moyen)}
    />
  );
}
