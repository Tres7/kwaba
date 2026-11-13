"use client";

import Link from "next/link";
import { ArrowLeft, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCoverage } from "../hooks";
import type { DelayStats } from "../types";

function hours(stats: DelayStats): string {
  if (stats.median_h === null) return "-";
  return stats.median_h >= 48 ? `${Math.round(stats.median_h / 24)} j` : `${stats.median_h} h`;
}

export default function Coverage() {
  const { data, isLoading, isError } = useCoverage();

  return (
    <div className="max-w-4xl">
      <Link href="/agent/agenda" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand">
        <ArrowLeft size={16} aria-hidden /> Agenda
      </Link>
      <h1 className="font-heading font-bold text-2xl text-dark mt-3">Couverture et délais</h1>
      <p className="text-sm text-gray-500 mt-1">Créneaux libres sur les 14 prochains jours, par ville, tous agents confondus.</p>
      {isLoading && <p className="mt-6 text-sm text-gray-500">Chargement…</p>}
      {isError && <p className="mt-6 text-sm text-red-700">La couverture n&apos;a pas pu être chargée.</p>}
      {data && (
        <>
          <section className="grid sm:grid-cols-3 gap-3 mt-6" aria-label="Délais médians">
            {([
              ["Annonce → rendez-vous", data.delays.listing_to_booking],
              ["Rendez-vous → visite", data.delays.booking_to_visit],
              ["Visite → décision", data.delays.visit_to_decision],
            ] as const).map(([label, stats]) => (
              <div key={label} className="rounded-2xl bg-surface shadow-xs p-4">
                <p className="text-xs font-semibold text-gray-500">{label}</p>
                <p className="font-heading font-bold text-2xl text-dark mt-1">{hours(stats)}</p>
                <p className="text-xs text-gray-500">médiane sur {stats.count} visite{stats.count > 1 ? "s" : ""}</p>
              </div>
            ))}
          </section>
          <p className="text-xs text-gray-500 mt-2">
            {data.delays.days} derniers jours · {data.delays.total} rendez-vous, dont {data.delays.by_phone} fixés par téléphone.
          </p>

          <div className="mt-6 rounded-3xl bg-surface shadow-xs overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500">
                  <th className="px-5 py-3 font-semibold">Ville</th>
                  <th className="px-5 py-3 font-semibold">Agents</th>
                  <th className="px-5 py-3 font-semibold text-right">Créneaux libres</th>
                  <th className="px-5 py-3 font-semibold text-right">Visites prévues</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.cities.map((row) => (
                  <tr key={row.city}>
                    <td className="px-5 py-3 font-semibold text-dark">{row.city}</td>
                    <td className="px-5 py-3 text-dark">{row.agents.map((a) => a.name).join(", ") || "-"}</td>
                    <td className={cn("px-5 py-3 text-right font-bold", row.free_slots === 0 ? "text-red-700" : "text-dark")}>
                      {row.free_slots === 0 && <TriangleAlert size={14} className="inline mr-1 -mt-0.5" aria-label="Ville sans créneau" />}
                      {row.free_slots}
                    </td>
                    <td className="px-5 py-3 text-right text-dark">{row.upcoming_visits}</td>
                  </tr>
                ))}
                {data.cities.length === 0 && (
                  <tr><td colSpan={4} className="px-5 py-6 text-center text-gray-500">Aucun agent n&apos;a encore indiqué ses villes.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
