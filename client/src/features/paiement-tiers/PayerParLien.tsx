"use client";

import { useParams } from "next/navigation";
import { demarrerPaiementTiers, lireApercuTiers } from "./api";
import PayerPourAutrui from "./PayerPourAutrui";

/** Page of the secret link the traveller sent: /payer/<link>. */
export default function PayerParLien() {
  const { jeton } = useParams<{ jeton: string }>();
  return (
    <PayerPourAutrui
      cle={["paiement-tiers", "lien", jeton]}
      charger={() => lireApercuTiers(jeton)}
      demarrer={(moyen) => demarrerPaiementTiers(jeton, moyen)}
    />
  );
}
