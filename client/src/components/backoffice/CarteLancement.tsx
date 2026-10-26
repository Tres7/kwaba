"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MailCheck } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";

interface Lancement {
  inscrits: number;
  a_prevenir: number;
  logements_publies: number;
}

/** Opening waiting list: visitors signed up through the "Places to stay coming soon" window. */
export default function CarteLancement() {
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["admin", "lancement"],
    queryFn: async () => (await api.get<Lancement>("/v1/admin/lancement/")).data,
  });
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);

  // Once everybody has been notified, the card is no longer useful
  if (!data || (data.inscrits > 0 && data.a_prevenir === 0) || (data.inscrits === 0 && data.logements_publies > 0)) return null;
  const pret = data.logements_publies > 0 && data.a_prevenir > 0;

  return (
    <section className="bg-white rounded-2xl border border-gray-100 p-5 flex flex-col sm:flex-row sm:items-center gap-4">
      <span className="w-11 h-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><MailCheck size={20} aria-hidden /></span>
      <div className="flex-1 min-w-0">
        <h2 className="font-heading font-bold text-dark">Liste d&apos;attente de l&apos;ouverture</h2>
        <p className="text-sm text-muted mt-0.5">
          {data.inscrits} visiteur{data.inscrits > 1 ? "s" : ""} inscrit{data.inscrits > 1 ? "s" : ""}, {data.a_prevenir} à prévenir.{" "}
          {data.logements_publies === 0
            ? "La fenêtre « Logements bientôt disponibles » s'affiche tant qu'aucun logement n'est publié."
            : `${data.logements_publies} logement${data.logements_publies > 1 ? "s" : ""} publié${data.logements_publies > 1 ? "s" : ""} : vous pouvez prévenir les inscrits.`}
        </p>
      </div>
      <button type="button" disabled={!pret} onClick={() => setConfirmation({
        titre: "Prévenir les inscrits",
        message: <>Un email « Les logements sont en ligne » part à <strong>{data.a_prevenir}</strong> personne{data.a_prevenir > 1 ? "s" : ""}. Personne n&apos;est prévenu deux fois.</>,
        libelle: "Envoyer",
        action: async () => {
          try {
            const { data: r } = await api.post<{ envoyes: number }>("/v1/admin/lancement/");
            toast.success(`${r.envoyes} email${r.envoyes > 1 ? "s" : ""} envoyé${r.envoyes > 1 ? "s" : ""}`);
            queryClient.invalidateQueries({ queryKey: ["admin", "lancement"] });
          } catch (err) {
            toast.error(apiErrorMessage(err));
            throw err;
          }
        },
      })} className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-40">
        Prévenir les inscrits
      </button>
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </section>
  );
}
