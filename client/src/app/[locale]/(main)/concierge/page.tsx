"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Loader2, MessageSquarePlus, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage, jetonAcces } from "@/lib/api";
import { getApiBaseUrl } from "@/lib/api-url";
import { cn } from "@/lib/utils";
import TexteConcierge from "@/components/concierge/TexteConcierge";
import CartesConcierge from "@/components/concierge/CartesConcierge";
import type { Carte, ConversationResume, MessageConcierge } from "@/types/api/concierge";
import { useLocale, useTranslations } from "next-intl";

const SUGGESTIONS = [
  "s1",
  "s2",
  "s3",
  "s4",
];

interface EnCours {
  texte: string;
  outil: string | null;
  cartes: Carte[];
}

/** Reads an SSE stream ("event: … / data: …" events) and calls `surEvenement` for each one. */
async function lireFlux(reponse: Response, surEvenement: (nom: string, donnees: Record<string, unknown>) => void) {
  const lecteur = reponse.body!.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  for (;;) {
    const { done, value } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    let fin;
    while ((fin = tampon.indexOf("\n\n")) >= 0) {
      const bloc = tampon.slice(0, fin);
      tampon = tampon.slice(fin + 2);
      const nom = bloc.match(/^event: (.+)$/m)?.[1];
      const data = bloc.match(/^data: (.+)$/m)?.[1];
      if (nom && data) surEvenement(nom, JSON.parse(data));
    }
  }
}

function ConciergeContent() {
  const t = useTranslations("concierge");
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { status } = useSession();
  const connecte = status === "authenticated";
  const conversationId = searchParams.get("c");
  const [saisie, setSaisie] = useState("");
  const [enCours, setEnCours] = useState<EnCours | null>(null);
  const [enAttente, setEnAttente] = useState<string | null>(null);
  const filRef = useRef<HTMLDivElement>(null);
  const zoneRef = useRef<HTMLTextAreaElement>(null);

  const { data: statut } = useQuery({
    queryKey: ["concierge", "statut"],
    queryFn: async () => (await api.get<{ actif: boolean }>("/v1/concierge/statut/")).data,
  });
  const { data: conversations = [] } = useQuery({
    queryKey: ["concierge", "conversations"],
    queryFn: async () => (await api.get<{ results: ConversationResume[] }>("/v1/concierge/conversations/")).data.results,
    enabled: connecte,
  });
  const { data: messages = [] } = useQuery({
    queryKey: ["concierge", "conversation", conversationId],
    queryFn: async () => (await api.get<{ messages: MessageConcierge[] }>(`/v1/concierge/conversations/${conversationId}/`)).data.messages,
    enabled: connecte && !!conversationId,
  });

  useEffect(() => {
    // Scrolls the thread only: scrollIntoView would also scroll the page (down to the footer on phones)
    const fil = filRef.current;
    fil?.scrollTo({ top: fil.scrollHeight, behavior: "smooth" });
  }, [messages.length, enCours?.texte, enCours?.cartes.length, enAttente]);

  const envoyer = useCallback(async (texte: string) => {
    const message = texte.trim();
    if (!message || enCours) return;
    setSaisie("");
    setEnAttente(message);
    setEnCours({ texte: "", outil: null, cartes: [] });
    try {
      let id = conversationId;
      if (!id) {
        id = (await api.post<{ id: string }>("/v1/concierge/conversations/")).data.id;
        router.replace(`/concierge?c=${id}`);
      }
      const jeton = await jetonAcces();
      const reponse = await fetch(`${getApiBaseUrl()}/v1/concierge/conversations/${id}/messages/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept-Language": locale, ...(jeton ? { Authorization: `Bearer ${jeton}` } : {}) },
        body: JSON.stringify({ texte: message }),
      });
      if (!reponse.ok) {
        const corps = await reponse.json().catch(() => ({}));
        throw new Error(corps.detail || corps.texte?.[0] || t("erreurReponse"));
      }
      await lireFlux(reponse, (nom, d) => {
        if (nom === "texte") setEnCours((c) => c && { ...c, texte: c.texte + (d.delta as string), outil: null });
        else if (nom === "outil") setEnCours((c) => c && { ...c, outil: d.libelle as string });
        else if (nom === "cartes") setEnCours((c) => c && { ...c, cartes: d.cartes as Carte[] });
        else if (nom === "reprise") setEnCours((c) => c && { ...c, outil: t("reprise") });
        else if (nom === "refus" || nom === "erreur") {
          // Partial answer dropped: only the explanation message is shown
          setEnCours(null);
          toast.error(d.message as string);
        }
      });
      await queryClient.invalidateQueries({ queryKey: ["concierge", "conversation", id] });
      queryClient.invalidateQueries({ queryKey: ["concierge", "conversations"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : apiErrorMessage(err, t("erreurReponse")));
      setSaisie(message);
    } finally {
      setEnCours(null);
      setEnAttente(null);
      zoneRef.current?.focus();
    }
  }, [conversationId, enCours, queryClient, router, locale, t]);

  const supprimer = async (id: string) => {
    if (!window.confirm(t("supprimerQuestion"))) return;
    await api.delete(`/v1/concierge/conversations/${id}/`);
    queryClient.invalidateQueries({ queryKey: ["concierge", "conversations"] });
    if (id === conversationId) router.replace("/concierge");
  };

  if (status === "unauthenticated") {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 bg-light">
        <div className="max-w-md text-center bg-white rounded-3xl border border-gray-100 shadow-card p-8">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-primary/10 text-primary flex items-center justify-center"><Sparkles size={26} /></div>
          <h1 className="font-heading font-bold text-dark text-2xl mt-4">Kwa-Ba Concierge</h1>
          <p className="text-gray-600 mt-2">{t("presentation")}</p>
          <Link href="/login?callbackUrl=/concierge" className="inline-block mt-6 bg-primary text-white font-bold px-6 py-3 rounded-xl">{t("seConnecter")}</Link>
        </div>
      </div>
    );
  }

  const vide = !conversationId && !enAttente;

  return (
    <div className="bg-light">
      <div className="max-w-6xl mx-auto px-0 sm:px-6 lg:py-6 flex gap-6 h-[calc(100dvh-4rem)] md:h-[calc(100dvh-5rem)]">
        <aside className="hidden lg:flex w-64 flex-shrink-0 flex-col bg-white rounded-3xl border border-gray-100 p-3">
          <button onClick={() => router.push("/concierge")} className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-primary text-white text-sm font-bold">
            <MessageSquarePlus size={16} /> {t("nouvelleConversation")}
          </button>
          <ul className="mt-3 flex-1 overflow-y-auto space-y-1">
            {conversations.map((c) => (
              <li key={c.id} className="group flex items-center">
                <Link href={`/concierge?c=${c.id}`} className={cn("flex-1 min-w-0 px-3 py-2 rounded-xl text-sm truncate", c.id === conversationId ? "bg-primary/10 text-primary font-semibold" : "text-dark hover:bg-gray-50")}>
                  {c.titre}
                </Link>
                <button onClick={() => supprimer(c.id)} aria-label={`Supprimer la conversation ${c.titre}`} className="p-1.5 text-gray-400 hover:text-red-700 opacity-0 group-hover:opacity-100 focus:opacity-100">
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="flex-1 min-w-0 flex flex-col bg-white sm:rounded-3xl sm:border sm:border-gray-100 overflow-hidden">
          <header className="flex items-center justify-between gap-3 px-4 sm:px-6 py-3 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-xl bg-primary text-white flex items-center justify-center"><Sparkles size={18} /></div>
              <div>
                <h1 className="font-heading font-bold text-dark leading-tight">Kwa-Ba Concierge</h1>
                <p className="text-[11px] text-gray-600">{t("avertissement")}</p>
              </div>
            </div>
            {conversationId && (
              <button onClick={() => router.push("/concierge")} className="lg:hidden flex items-center gap-1.5 text-xs font-bold text-primary">
                <MessageSquarePlus size={15} /> {t("nouvelle")}
              </button>
            )}
          </header>

          <div ref={filRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-5 space-y-5" aria-live="polite">
            {statut && !statut.actif && (
              <p className="text-sm text-amber-900 bg-amber-50 rounded-xl px-4 py-3">{t("inactif")}</p>
            )}
            {vide ? (
              <div className="max-w-xl mx-auto text-center pt-6">
                <h2 className="font-heading font-bold text-dark text-2xl">{t("ouPartez")}</h2>
                <p className="text-gray-600 mt-2 text-sm">
                  {t("accroche")}
                </p>
                <div className="grid sm:grid-cols-2 gap-2 mt-6 text-left">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => envoyer(t(`suggestions.${s}`))} disabled={!statut?.actif}
                      className="text-sm text-dark bg-gray-50 hover:bg-primary/5 border border-gray-100 rounded-2xl p-3 disabled:opacity-50">
                      {t(`suggestions.${s}`)}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((m) => <Bulle key={m.id} role={m.role} texte={m.texte} cartes={m.cartes} />)}
                {/* First message of a conversation: the reloaded history already contains it, do not show it twice */}
                {enAttente && !(messages.at(-1)?.role === "user" && messages.at(-1)?.texte === enAttente) && (
                  <Bulle role="user" texte={enAttente} cartes={[]} />
                )}
                {enCours && (
                  <div className="space-y-3">
                    {(enCours.texte || !enCours.outil) && (
                      <Bulle role="assistant" texte={enCours.texte} cartes={[]} enCours />
                    )}
                    {enCours.outil && (
                      <p className="flex items-center gap-2 text-sm text-gray-600"><Loader2 size={15} className="animate-spin text-primary" /> {enCours.outil}…</p>
                    )}
                    <CartesConcierge cartes={enCours.cartes} />
                  </div>
                )}
              </>
            )}
          </div>

          <form method="post" onSubmit={(e) => { e.preventDefault(); envoyer(saisie); }} className="border-t border-gray-100 p-3 sm:p-4">
            <div className="flex items-end gap-2 bg-gray-50 border border-gray-200 rounded-2xl px-3 py-2 focus-within:border-primary/50">
              <label htmlFor="concierge-saisie" className="sr-only">{t("votreMessage")}</label>
              <textarea
                id="concierge-saisie" ref={zoneRef} rows={1} value={saisie} maxLength={2000}
                onChange={(e) => setSaisie(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(saisie); } }}
                placeholder={t("placeholder")}
                disabled={!statut?.actif}
                className="flex-1 resize-none bg-transparent outline-none text-base sm:text-sm text-dark max-h-40 py-1.5"
              />
              <button type="submit" disabled={!saisie.trim() || !!enCours || !statut?.actif} aria-label={t("envoyer")}
                className="relative zone-tactile w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 disabled:opacity-40">
                {enCours ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={18} />}
              </button>
            </div>
            <p className="text-[11px] text-gray-600 mt-1.5 text-center">
              {t("gemini")} <Link href="/confidentialite#destinataires" className="relative zone-tactile underline">{t("enSavoirPlus")}</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}

function Bulle({ role, texte, cartes, enCours }: { role: "user" | "assistant"; texte: string; cartes: Carte[]; enCours?: boolean }) {
  const tB = useTranslations("concierge");
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] sm:max-w-[70%] bg-primary text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm whitespace-pre-wrap">{texte}</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {(texte || enCours) && (
        <div className="max-w-[92%] sm:max-w-[80%] text-sm text-dark">
          {texte ? <TexteConcierge texte={texte} /> : <Loader2 size={16} className="animate-spin text-primary" aria-label={tB("ecrit")} />}
        </div>
      )}
      <CartesConcierge cartes={cartes} />
    </div>
  );
}

export default function ConciergePage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] bg-light" />}>
      <ConciergeContent />
    </Suspense>
  );
}
