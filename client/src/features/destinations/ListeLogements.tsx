"use client";

import PropertyCard from "@/components/hebergement/PropertyCard";
import type { Hebergement } from "@/types/api/models";

/** Listing cards of a destination page: PropertyCard reads client contexts (favourites, details), so it is rendered here. */
export default function ListeLogements({ logements }: { logements: Hebergement[] }) {
  return (
    <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      {logements.map((h) => <li key={h.id}><PropertyCard property={h} /></li>)}
    </ul>
  );
}
