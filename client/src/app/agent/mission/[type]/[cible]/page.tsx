"use client";

import { useParams } from "next/navigation";
import PhoneBooking from "@/features/agenda/admin/PhoneBooking";
import FicheMission from "@/features/verifications/admin/FicheMission";

export default function FicheMissionPage() {
  const { type, cible } = useParams<{ type: string; cible: string }>();
  return (
    <>
      <FicheMission />
      {type === "logement" && <PhoneBooking listingId={cible} />}
    </>
  );
}
