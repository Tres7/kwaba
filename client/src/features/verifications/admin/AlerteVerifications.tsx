"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { House, IdCard, X } from "lucide-react";
import type { CompteursVerification } from "../compteurs";

const PREFIXE = /^\(\d+\) /;

function Notification({ id, icone: Icone, titre, texte }: { id: string | number; icone: typeof IdCard; titre: string; texte: string }) {
  return (
    <div className="w-full sm:w-[380px] flex gap-3 rounded-2xl bg-primary-800 text-white p-4 shadow-card-hover">
      <span className="w-10 h-10 flex-shrink-0 rounded-xl bg-white/10 flex items-center justify-center"><Icone size={20} aria-hidden /></span>
      <div className="flex-1 min-w-0">
        <p className="font-heading font-bold text-[15px] leading-snug">{titre}</p>
        <p className="text-sm text-white/80 mt-0.5">{texte}</p>
        <Link href="/agent/a-faire" onClick={() => toast.dismiss(id)} className="inline-block mt-2 text-sm font-bold underline underline-offset-2">
          Voir les vérifications
        </Link>
      </div>
      <button type="button" onClick={() => toast.dismiss(id)} aria-label="Fermer la notification"
        className="w-8 h-8 -mt-1 -mr-1 flex-shrink-0 rounded-full flex items-center justify-center text-white/80 hover:text-white hover:bg-white/10">
        <X size={18} aria-hidden />
      </button>
    </div>
  );
}

function notifier(icone: typeof IdCard, titre: string, texte: string) {
  toast.custom((id) => <Notification id={id} icone={icone} titre={titre} texte={texte} />, { position: "top-right", duration: 15_000 });
}

/**
 * While an admin or agent works (back-office or agent space): a notification when a new identity document or a new
 * listing to visit arrives, the agent lists refreshed, and the number of pending items in the tab title.
 */
export default function AlerteVerifications({ compteurs }: { compteurs?: CompteursVerification }) {
  const queryClient = useQueryClient();
  const pathname = usePathname();
  const precedents = useRef<CompteursVerification | null>(null);

  useEffect(() => {
    if (!compteurs) return;
    const avant = precedents.current;
    precedents.current = compteurs;
    if (!avant) return; // first load: nothing is "new"
    if (compteurs.pieces > avant.pieces) {
      notifier(IdCard, "Nouvelle pièce d'identité à contrôler", "Un hôte vient d'envoyer ses pièces justificatives.");
    }
    if (compteurs.visites > avant.visites) {
      notifier(House, "Nouvelle annonce à visiter", "Un logement attend la visite d'un agent.");
    }
    if (compteurs.pieces !== avant.pieces || compteurs.visites !== avant.visites) {
      queryClient.invalidateQueries({ queryKey: ["agent"] });
    }
  }, [compteurs, queryClient]);

  // "(2) Back-office · Kwa-Ba": kept when Next.js rewrites the title after a navigation
  const total = compteurs?.total ?? 0;
  useEffect(() => {
    const appliquer = () => {
      const base = document.title.replace(PREFIXE, "");
      const voulu = total > 0 ? `(${total}) ${base}` : base;
      if (document.title !== voulu) document.title = voulu;
    };
    appliquer();
    const titre = document.querySelector("title");
    const observateur = titre ? new MutationObserver(appliquer) : null;
    if (titre) observateur?.observe(titre, { childList: true, characterData: true, subtree: true });
    return () => {
      observateur?.disconnect();
      document.title = document.title.replace(PREFIXE, "");
    };
  }, [total, pathname]);

  return null;
}
