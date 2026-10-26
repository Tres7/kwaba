"use client";

import { useState } from "react";
import { cn, formatDate, formatPrice } from "@/lib/utils";
import type { AdminStats } from "@/types/api/admin";

type Jour = AdminStats["reservations_par_jour"][number];

// primary-600: contrast ≥ 3:1 on a light background (validated), unlike the base orange
const BARRE = "#CC6C1B";
const HAUTEUR = 160;

/** Confirmed bookings per day over 30 days: thin bars, tooltip on hover / focus, table view. */
export default function ReservationsChart({ jours }: { jours: Jour[] }) {
  const [survol, setSurvol] = useState<number | null>(null);
  const [tableau, setTableau] = useState(false);
  const max = Math.max(1, ...jours.map((j) => j.nombre));
  // Without duplicates: with max = 1 the middle line would also be 1 (two "1" on the axis, same React key)
  const graduations = [...new Set([0, Math.ceil(max / 2), max])];
  const courant = survol !== null ? jours[survol] : null;

  return (
    <div>
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="font-heading font-bold text-dark">Réservations confirmées (30 derniers jours)</h2>
        <button onClick={() => setTableau(!tableau)} className="text-xs font-semibold text-primary hover:underline flex-shrink-0">
          {tableau ? "Voir le graphique" : "Voir le tableau"}
        </button>
      </div>

      {tableau ? (
        <div className="max-h-72 overflow-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-muted uppercase"><th className="py-2">Jour</th><th className="py-2 text-right">Réservations</th><th className="py-2 text-right">Volume</th></tr></thead>
            <tbody>
              {jours.map((j) => (
                <tr key={j.date} className="border-t border-gray-100">
                  <td className="py-1.5">{formatDate(j.date, { weekday: "short", day: "numeric", month: "short" })}</td>
                  <td className="py-1.5 text-right tabular-nums">{j.nombre}</td>
                  <td className="py-1.5 text-right tabular-nums">{formatPrice(j.volume)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative">
          {/* Tooltip: value first, label next */}
          <div className={cn("absolute -top-1 right-0 text-right transition-opacity pointer-events-none", courant ? "opacity-100" : "opacity-0")} aria-live="polite">
            {courant && (
              <>
                <p className="text-sm font-bold text-dark tabular-nums">{courant.nombre} réservation{courant.nombre > 1 ? "s" : ""} · {formatPrice(courant.volume)}</p>
                <p className="text-xs text-muted">{formatDate(courant.date, { weekday: "long", day: "numeric", month: "long" })}</p>
              </>
            )}
          </div>

          <div className="flex gap-2 pt-10">
            <div className="flex flex-col justify-between text-[11px] text-muted tabular-nums text-right w-5" style={{ height: HAUTEUR }} aria-hidden>
              {[...graduations].reverse().map((g) => <span key={g} className="leading-none">{g}</span>)}
            </div>
            <div className="relative flex-1" style={{ height: HAUTEUR }}>
              {graduations.map((g) => (
                <div key={g} className="absolute inset-x-0 border-t border-gray-100" style={{ bottom: `${(g / max) * 100}%` }} aria-hidden />
              ))}
              <div className="absolute inset-0 flex items-end gap-[2px]" onMouseLeave={() => setSurvol(null)}>
                {jours.map((j, i) => (
                  <button
                    key={j.date} type="button"
                    onMouseEnter={() => setSurvol(i)} onFocus={() => setSurvol(i)} onBlur={() => setSurvol(null)}
                    aria-label={`${formatDate(j.date, { day: "numeric", month: "long" })} : ${j.nombre} réservation(s), ${formatPrice(j.volume)}`}
                    className="flex-1 h-full flex items-end group focus:outline-none"
                  >
                    <span
                      className={cn("w-full rounded-t-[4px] transition-opacity", survol !== null && survol !== i && "opacity-40", "group-focus-visible:outline group-focus-visible:outline-2 group-focus-visible:outline-dark")}
                      style={{ height: j.nombre ? `${(j.nombre / max) * 100}%` : 2, background: j.nombre ? BARRE : "#e5e7eb" }}
                    />
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex justify-between text-[11px] text-muted mt-2 pl-7" aria-hidden>
            <span>{jours[0] && formatDate(jours[0].date, { day: "numeric", month: "short" })}</span>
            <span>Aujourd&apos;hui</span>
          </div>
        </div>
      )}
    </div>
  );
}
