"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { supprimerAvisAdmin } from "@/features/avis";
import { cn, formatDate } from "@/lib/utils";
import { PAGE_SIZE, useAdminList, useDebounced } from "@/lib/useAdminList";
import { ActionButton, Pagination, SearchInput } from "@/components/backoffice/AdminTable";
import ConfirmDialog, { type Confirmation } from "@/components/backoffice/ConfirmDialog";
import Select from "@/components/ui/Select";
import type { AdminAvis } from "@/types/api/admin";

const NOTES = [
  { value: "", label: "Toutes les notes" },
  ...[5, 4, 3, 2, 1].map((n) => ({ value: String(n), label: `${n} étoile${n > 1 ? "s" : ""}` })),
];

function Avis() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [note, setNote] = useState(searchParams.get("note") ?? "");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const recherche = useDebounced(q);

  const { data, isLoading, isFetching, isError, refetch, page, setPage } = useAdminList<AdminAvis>("avis", { q: recherche, note });

  const supprimer = (a: AdminAvis) => setConfirmation({
    titre: "Supprimer cet avis",
    message: <>L&apos;avis de <strong>{a.auteur.nom}</strong> sur <strong>{a.hebergement.name}</strong> sera retiré et la note du logement recalculée. À réserver aux contenus abusifs (insultes, données personnelles, hors sujet).</>,
    libelle: "Supprimer l'avis", danger: true, motif: true,
    action: async (motif) => {
      try {
        await supprimerAvisAdmin(a.id, motif);
        toast.success("Avis supprimé");
        queryClient.invalidateQueries({ queryKey: ["admin"] });
      } catch (err) {
        toast.error(apiErrorMessage(err));
        throw err;
      }
    },
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Avis</h1>
        <p className="text-muted text-sm mt-1">{data ? `${data.count} avis` : "…"}</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Texte de l'avis, annonce ou email de l'auteur" />
        <Select label="Note" value={note} onChange={setNote} options={NOTES} className="sm:w-48" />
      </div>

      {isError ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
          <p className="text-dark font-semibold mb-2">Impossible de charger les avis.</p>
          <button onClick={() => refetch()} className="text-primary font-bold hover:underline">Réessayer</button>
        </div>
      ) : isLoading && !data ? (
        <div className="space-y-3">{[0, 1, 2].map((i) => <div key={i} className="h-32 skeleton rounded-2xl" />)}</div>
      ) : !data?.results.length ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center text-muted">Aucun avis pour ces critères.</div>
      ) : (
        <ul className={cn("space-y-3 transition-opacity", isFetching && "opacity-60")}>
          {data.results.map((a) => (
            <li key={a.id} className="bg-white rounded-2xl border border-gray-100 p-5">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex gap-0.5" role="img" aria-label={`${a.note} sur 5`}>
                      {[1, 2, 3, 4, 5].map((i) => <Star key={i} size={14} className={i <= a.note ? "fill-accent text-accent" : "text-gray-300"} />)}
                    </span>
                    <Link href={`/hebergements/${a.hebergement.id}#avis`} target="_blank" className="text-sm font-semibold text-dark hover:text-primary truncate">{a.hebergement.name}</Link>
                  </div>
                  <p className="text-xs text-muted mt-1">{a.auteur.nom} · {a.auteur.email} · {formatDate(a.created_at)}</p>
                </div>
                <ActionButton danger onClick={() => supprimer(a)}>Supprimer</ActionButton>
              </div>
              <p className="text-sm text-gray-700 mt-3 whitespace-pre-line">{a.commentaire}</p>
              {a.reponse_hote && (
                <p className="text-sm text-gray-600 mt-3 pl-3 border-l-2 border-primary/30"><span className="font-semibold text-dark">Réponse de l&apos;hôte : </span>{a.reponse_hote}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={setPage} />}
      <ConfirmDialog confirmation={confirmation} onClose={() => setConfirmation(null)} />
    </div>
  );
}

export default function AvisAdminPage() {
  return <Suspense><Avis /></Suspense>;
}
