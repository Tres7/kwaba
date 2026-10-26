"use client";

import { useState } from "react";
import { Link, useRouter } from "@/i18n/navigation";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import Floating from "@/components/ui/Floating";
import { usePopover } from "@/lib/usePopover";
import { useModule } from "@/lib/site";
import type { VoyageResume } from "@/types/api/voyage";
import { useTranslations } from "next-intl";

/** Button of the listing page: suggest this listing to one of your group trips. */
export default function ProposerAuGroupe({ hebergementId }: { hebergementId: string }) {
  const t = useTranslations("proposerGroupe");
  const router = useRouter();
  const { status } = useSession();
  const { open, setOpen, ref, panelRef } = usePopover();
  const [envoi, setEnvoi] = useState<string | null>(null);
  const together = useModule("together");

  const { data: voyages = [] } = useQuery({
    queryKey: ["voyages"],
    queryFn: async () => (await api.get<{ results: VoyageResume[] }>("/v1/voyages/")).data.results,
    enabled: status === "authenticated" && together,
  });

  if (status !== "authenticated" || !together) return null;

  const proposer = async (v: VoyageResume) => {
    setEnvoi(v.id);
    try {
      await api.post(`/v1/voyages/${v.id}/propositions/`, { hebergement: hebergementId });
      toast.success(t("propose", { nom: v.nom }), { action: { label: t("voir"), onClick: () => router.push(`/together/${v.id}`) } });
      setOpen(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, t("erreur")));
    } finally {
      setEnvoi(null);
    }
  };

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)} aria-expanded={open} aria-haspopup="dialog"
        className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl border border-gray-200 text-sm font-bold text-dark hover:bg-gray-50">
        <Users size={16} /> {t("proposer")}
      </button>
      {open && (
        <Floating ref={panelRef} anchor={ref} onClose={() => setOpen(false)} label={t("proposerA")} className="p-2 w-72">
          {voyages.length === 0 ? (
            <div className="p-3 text-sm text-gray-600">
              {t("aucunVoyage")} <Link href="/together" className="text-primary font-bold">{t("creerVoyage")}</Link>
            </div>
          ) : (
            <ul>
              {voyages.map((v) => (
                <li key={v.id}>
                  <button onClick={() => proposer(v)} disabled={envoi === v.id}
                    className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-gray-50 disabled:opacity-50">
                    <span className="block text-sm font-bold text-dark">{v.nom}</span>
                    <span className="block text-xs text-gray-600">{v.destination} · {v.nb_membres} membre{v.nb_membres > 1 ? "s" : ""}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Floating>
      )}
    </div>
  );
}
