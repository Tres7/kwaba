"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Phone } from "lucide-react";
import { apiErrorMessage } from "@/lib/api";
import { bookByPhone } from "../api";
import { useAgendaMutation } from "../hooks";
import { dayKey } from "../time";

export default function PhoneBooking({ listingId }: { listingId: string }) {
  const [day, setDay] = useState("");
  const [time, setTime] = useState("09:00");
  const [booked, setBooked] = useState(false);
  const book = useAgendaMutation(() => bookByPhone(listingId, `${day}T${time}:00+00:00`));

  if (booked) {
    return (
      <p className="mt-4 rounded-2xl bg-primary/10 text-primary text-sm font-semibold p-4">
        Visite enregistrée et confirmée à l&apos;hôte. <Link href="/agent/agenda" className="underline">Voir mon agenda</Link>
      </p>
    );
  }

  return (
    <form className="mt-4 rounded-2xl bg-white border border-gray-100 shadow-sm p-4" onSubmit={(e) => {
      e.preventDefault();
      book.mutate(undefined, {
        onSuccess: () => { setBooked(true); toast.success("Visite confirmée par téléphone."); },
        onError: (err) => toast.error(apiErrorMessage(err, "Enregistrement impossible.")),
      });
    }}>
      <p className="flex items-center gap-2 font-bold text-dark"><Phone size={18} aria-hidden /> Fixer la visite par téléphone</p>
      <p className="text-sm text-gray-500 mt-1">
        L&apos;hôte n&apos;a pas réservé ou n&apos;a pas internet ? Convenez d&apos;un créneau par téléphone : il est ajouté à votre agenda et l&apos;hôte reçoit la confirmation.
      </p>
      <div className="flex flex-wrap items-end gap-2 mt-3">
        <label className="text-xs font-semibold text-gray-500">Date
          <input type="date" value={day} min={dayKey(new Date())} onChange={(e) => setDay(e.target.value)} required
            className="block mt-1 rounded-xl border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <label className="text-xs font-semibold text-gray-500">Heure
          <input type="time" value={time} step={900} onChange={(e) => setTime(e.target.value)} required
            className="block mt-1 rounded-xl border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <button type="submit" disabled={book.isPending} className="rounded-xl bg-primary text-white font-bold px-4 py-2.5 text-sm disabled:opacity-60">
          Confirmer la visite
        </button>
      </div>
    </form>
  );
}
