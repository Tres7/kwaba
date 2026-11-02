"use client";

import { useState } from "react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, MessageSquareReply, Star } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { cn, initials } from "@/lib/utils";
import type { Avis, CritereAvis } from "@/types/api/models";
import { useLocale, useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";
import { listerAvis, repondreAvis } from "./api";
import { clesAvis } from "./hooks";

const PAGE = 6;

function Stars({ value, size = 14 }: { value: number; size?: number }) {
  return (
    <span className="inline-flex gap-0.5" role="img" aria-label={`${value} sur 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star key={i} size={size} className={i <= Math.round(value) ? "fill-accent text-accent" : "text-gray-300"} />
      ))}
    </span>
  );
}

function ReponseForm({ avis, onDone }: { avis: Avis; onDone: (a: Avis) => void }) {
  const t = useTranslations("avis");
  const [open, setOpen] = useState(false);
  const [texte, setTexte] = useState("");
  const [envoi, setEnvoi] = useState(false);

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline">
        <MessageSquareReply size={15} /> {t("repondre")}
      </button>
    );
  }

  const envoyer = async () => {
    setEnvoi(true);
    try {
      onDone(await repondreAvis(avis.id, texte.trim()));
      toast.success(t("reponsePubliee"));
    } catch (err) {
      toast.error(apiErrorMessage(err));
      setEnvoi(false);
    }
  };

  return (
    <div className="mt-3 space-y-2">
      <textarea
        value={texte} onChange={(e) => setTexte(e.target.value)} rows={3} maxLength={1000}
        placeholder={t("reponsePlaceholder")}
        className="w-full border border-gray-200 rounded-xl px-3 py-2 text-base sm:text-sm outline-none focus:border-primary resize-none"
      />
      <div className="flex gap-2 justify-end">
        <button onClick={() => setOpen(false)} className="px-4 py-2 text-sm rounded-xl border border-gray-200">{t("annuler")}</button>
        <button onClick={envoyer} disabled={envoi || texte.trim().length < 2} className="px-4 py-2 text-sm rounded-xl bg-primary text-white font-bold disabled:opacity-50">
          {envoi ? t("publication") : t("publier")}
        </button>
      </div>
    </div>
  );
}

function AvisCard({ avis, isOwner, hostName, onUpdate }: { avis: Avis; isOwner: boolean; hostName: string; onUpdate: (a: Avis) => void }) {
  const { formatDate } = useFormat();
  const t = useTranslations("avis");
  const [deplie, setDeplie] = useState(false);
  const long = avis.commentaire.length > 280;
  const nom = `${avis.auteur.prenom} ${avis.auteur.initiale}`.trim();

  return (
    <article className="py-5 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center overflow-hidden flex-shrink-0">
          {avis.auteur.avatar_url ? <img src={avis.auteur.avatar_url} alt="" className="w-full h-full object-cover" /> : initials(nom)}
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-dark text-sm">{nom}</p>
          <p className="text-xs text-muted flex items-center gap-1 flex-wrap">
            <span className="inline-flex items-center gap-0.5 text-secondary font-semibold"><BadgeCheck size={12} /> {t("sejourVerifie")}</span>
            · {formatDate(avis.sejour, { month: "long", year: "numeric" })}
          </p>
        </div>
      </div>
      <div className="mt-3"><Stars value={avis.note} /></div>
      <p className={cn("text-sm text-gray-700 leading-relaxed mt-2 whitespace-pre-line", !deplie && long && "line-clamp-4")}>{avis.commentaire}</p>
      {long && (
        <button onClick={() => setDeplie(!deplie)} className="text-sm font-semibold text-dark underline mt-1">
          {deplie ? t("voirMoins") : t("lireSuite")}
        </button>
      )}

      {avis.reponse_hote ? (
        <div className="mt-3 ml-4 pl-4 border-l-2 border-primary/30">
          <p className="text-xs font-bold text-dark">{t("reponseDe", { hote: hostName })}</p>
          <p className="text-sm text-gray-600 mt-1 whitespace-pre-line">{avis.reponse_hote}</p>
        </div>
      ) : isOwner ? (
        <ReponseForm avis={avis} onDone={onUpdate} />
      ) : null}
    </article>
  );
}

interface AvisSectionProps {
  hebergementId: string;
  isOwner: boolean;
  hostName: string;
}

export default function AvisSection({ hebergementId, isOwner, hostName }: AvisSectionProps) {
  const t = useTranslations("avis");
  const locale = useLocale();
  const tNote = useTranslations("note");
  const queryClient = useQueryClient();
  const queryKey = clesAvis.hebergement(hebergementId);

  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey,
    initialPageParam: 0,
    queryFn: ({ pageParam }) => listerAvis(hebergementId, { limit: PAGE, offset: pageParam }),
    getNextPageParam: (last, pages) => {
      const charges = pages.reduce((n, p) => n + p.results.length, 0);
      return charges < last.count ? charges : undefined;
    },
  });

  const remplacer = (maj: Avis) =>
    queryClient.setQueryData<typeof data>(queryKey, (old) =>
      old && { ...old, pages: old.pages.map((p) => ({ ...p, results: p.results.map((a) => (a.id === maj.id ? maj : a)) })) }
    );

  if (isLoading) return <section id="avis" className="bg-white rounded-2xl shadow-card p-5 sm:p-6"><div className="h-40 skeleton rounded-xl" /></section>;

  const resume = data?.pages[0]?.resume;
  const avis = data?.pages.flatMap((p) => p.results) ?? [];

  return (
    <section id="avis" className="bg-white rounded-2xl shadow-card p-5 sm:p-6 scroll-mt-24">
      <h2 className="font-heading font-bold text-dark text-xl mb-1">{t("titre")}</h2>
      <p className="text-xs text-muted mb-5 flex items-center gap-1">
        <BadgeCheck size={13} className="text-secondary" /> {t("uniquementSejournes")}
      </p>

      {!resume || resume.total === 0 ? (
        <div className="bg-light-muted rounded-xl p-5 text-sm text-gray-600">
          <p className="font-semibold text-dark mb-1">{t("pasEncore")}</p>
          {t("nouveau")}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-[auto_1fr_1fr] gap-6 pb-6 border-b border-gray-100">
            <div className="flex md:flex-col items-center md:items-start gap-3 md:gap-1">
              <p className="font-heading font-bold text-5xl text-dark leading-none">
                {resume.moyenne?.toLocaleString(locale === "en" ? "en-GB" : "fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
              </p>
              <div>
                <Stars value={resume.moyenne ?? 0} size={16} />
                <p className="text-sm text-muted mt-1">{tNote("avis", { nombre: resume.total })}</p>
              </div>
            </div>

            <div className="space-y-1.5" aria-label={t("repartition")}>
              {[5, 4, 3, 2, 1].map((n) => {
                const nb = resume.repartition[String(n)] ?? 0;
                return (
                  <div key={n} className="flex items-center gap-2 text-xs">
                    <span className="w-3 text-muted">{n}</span>
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-accent rounded-full" style={{ width: `${(nb / resume.total) * 100}%` }} />
                    </div>
                    <span className="w-6 text-right text-muted">{nb}</span>
                  </div>
                );
              })}
            </div>

            <dl className="grid grid-cols-1 gap-1.5 text-sm">
              {(Object.keys(resume.libelles) as CritereAvis[]).map((c) => (
                <div key={c} className="flex items-center justify-between gap-3">
                  <dt className={cn("text-gray-600", c === "conformite" && "font-semibold text-dark")}>{t(`criteres.${c}`)}</dt>
                  <dd className="font-bold text-dark">{resume.criteres[c]?.toLocaleString(locale === "en" ? "en-GB" : "fr-FR", { minimumFractionDigits: 1 }) ?? "–"}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div>
            {avis.map((a) => <AvisCard key={a.id} avis={a} isOwner={isOwner} hostName={hostName} onUpdate={remplacer} />)}
          </div>

          {hasNextPage && (
            <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage} className="mt-2 w-full sm:w-auto px-6 py-3 rounded-xl border border-gray-300 text-sm font-semibold text-dark hover:bg-gray-50 disabled:opacity-50">
              {isFetchingNextPage ? t("chargement") : t("voirPlusAvis", { nombre: resume.total - avis.length })}
            </button>
          )}
        </>
      )}
    </section>
  );
}
