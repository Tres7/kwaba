"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Send, ShieldCheck, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useFormat } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";
import { envoyerMessage, lireConversation, listerMessages, marquerLu } from "./api";
import type { MessagingConversation, MessagingMessage } from "./types";
import { useTranslations } from "next-intl";

const CHAT_POLL_INTERVAL_MS = 4_000;

type ChatMessage = MessagingMessage & { pending?: boolean };

function errorMessage(err: unknown, t: ReturnType<typeof useTranslations<"messages">>): string {
  const response = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
  if (response?.status === 429) return t("tropDeMessages");
  return response?.data?.detail ?? t("nonEnvoye");
}

export default function ChatPage() {
  const t = useTranslations("messages");
  const { langue } = useFormat();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const conversationId = params.id;

  const [conversation, setConversation] = useState<MessagingConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [sendError, setSendError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  // Highest message id confirmed by the server: polling cursor
  const lastIdRef = useRef(0);

  // Adds server messages without duplicates (a sent message may come back both from the POST and from the polling)
  const mergeMessages = useCallback((incoming: MessagingMessage[]) => {
    if (incoming.length === 0) return;
    lastIdRef.current = Math.max(lastIdRef.current, ...incoming.map((m) => m.id));
    setMessages((prev) => {
      const known = new Set(prev.filter((m) => !m.pending).map((m) => m.id));
      const fresh = incoming.filter((m) => !known.has(m.id));
      if (fresh.length === 0) return prev;
      const confirmed = [...prev.filter((m) => !m.pending), ...fresh].sort((a, b) => a.id - b.id);
      return [...confirmed, ...prev.filter((m) => m.pending)];
    });
  }, []);

  const markAsRead = useCallback(() => {
    if (lastIdRef.current === 0) return;
    // Up to the last displayed message, not the last message in the database
    marquerLu(conversationId, lastIdRef.current).catch(() => {});
  }, [conversationId]);

  useEffect(() => {
    Promise.all([lireConversation(conversationId), listerMessages(conversationId)])
      .then(([lue, recus]) => {
        setConversation(lue);
        mergeMessages(recus);
        markAsRead();
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [conversationId, mergeMessages, markAsRead]);

  const pollNewMessages = useCallback(async () => {
    const incoming = await listerMessages(conversationId, lastIdRef.current);
    mergeMessages(incoming);
    if (incoming.some((m) => !m.is_own)) markAsRead();
  }, [conversationId, mergeMessages, markAsRead]);

  usePolling(pollNewMessages, CHAT_POLL_INTERVAL_MS, !loading && !notFound);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const content = input.trim();
    if (!content) return;
    setSendError("");

    // Shown immediately, replaced by the server version when the response arrives
    const tempId = -Date.now();
    setMessages((prev) => [...prev, {
      id: tempId, conversation_id: conversationId, sender_id: "", content,
      created_at: new Date().toISOString(), is_own: true, pending: true,
    }]);
    setInput("");

    try {
      const envoye = await envoyerMessage(conversationId, content);
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      mergeMessages([envoye]);
      if (envoye.masked) toast.info(t("masqueEnvoi"));
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      setInput(content);
      setSendError(errorMessage(err, t));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted">{t("chargement")}</p>
      </div>
    );
  }

  if (notFound || !conversation) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-muted">{t("introuvable")}</p>
        <Link href="/messages" className="text-primary font-medium hover:underline">{t("retour")}</Link>
      </div>
    );
  }

  const other = conversation.other_participant;
  const otherName = other ? `${other.first_name} ${other.last_name}`.trim() : "Utilisateur";
  const initial = otherName[0];

  return (
    <div className="min-h-screen bg-light flex flex-col">
      <div className="max-w-4xl w-full mx-auto flex flex-col flex-1 min-h-0 bg-white md:border-x border-light shadow-sm">
        {/* Header */}
        <div className="bg-white border-b border-light px-6 py-4 flex items-center justify-between gap-4 flex-shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-4 min-w-0">
            <button onClick={() => router.push("/messages")} className="text-dark hover:text-primary transition-colors p-1.5 -ml-1.5 rounded-full hover:bg-light">
              <ArrowLeft size={22} />
            </button>
            <div className="w-12 h-12 bg-gradient-to-br from-primary to-primary-600 rounded-full flex items-center justify-center shadow-sm flex-shrink-0 overflow-hidden">
              {other?.avatar_url ? (
                <img src={other.avatar_url} alt={otherName} className="w-full h-full object-cover" />
              ) : (
                <span className="text-white font-bold text-lg">{initial}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-heading font-bold text-dark text-lg truncate">{otherName}</p>
              <p className="text-muted text-xs font-medium truncate">
                {conversation.my_role === "host" ? t("voyageur") : t("hote")}
                {conversation.hebergement && (
                  <>
                    {" • "}
                    <Link href={`/hebergements/${conversation.hebergement.id}`} className="hover:text-primary hover:underline">
                      {conversation.hebergement.name}
                    </Link>
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Messaging rules: contact details hidden, traveller anonymous before payment */}
        <div className="bg-primary/5 border-b border-primary/10 px-4 md:px-6 py-2.5 text-xs text-dark space-y-1 flex-shrink-0">
          <p className="flex gap-2"><ShieldCheck size={15} className="text-primary flex-shrink-0 mt-px" aria-hidden /> {t("securite")}</p>
          {!conversation.booked && (
            <p className="flex gap-2 text-muted">
              <EyeOff size={15} className="flex-shrink-0 mt-px" aria-hidden />
              {conversation.my_role === "host" ? t("anonymeHote") : t("anonymeVoyageur")}
            </p>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-8 space-y-6 bg-gray-50/50">
          {messages.length === 0 && (
            <p className="text-center text-muted text-sm py-12">
              {t("premierMessage", { nom: otherName })}
            </p>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex gap-3", msg.is_own ? "justify-end" : "justify-start")}>
              {!msg.is_own && (
                <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary-600 rounded-full flex items-center justify-center flex-shrink-0 self-end shadow-sm mb-1">
                  <span className="text-white text-xs font-bold">{initial}</span>
                </div>
              )}
              <div className={cn(
                "max-w-[75%] md:max-w-[65%] px-5 py-3.5 text-[15px] leading-relaxed relative group",
                msg.is_own
                  ? "bg-primary text-white rounded-2xl rounded-br-sm shadow-md"
                  : "bg-white text-dark shadow-card rounded-2xl rounded-bl-sm border border-gray-100",
                msg.pending && "opacity-60"
              )}>
                <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                {msg.masked && (
                  <p className={cn("flex items-center gap-1 mt-1 text-[11px] font-medium", msg.is_own ? "text-white/80" : "text-muted")}>
                    <ShieldCheck size={12} aria-hidden /> {t("masque")}
                  </p>
                )}
                <div className={cn("flex items-center gap-1.5 mt-1.5", msg.is_own ? "justify-end" : "justify-start")}>
                  <p className={cn("text-[11px] font-medium", msg.is_own ? "text-white/70" : "text-muted/70")}>
                    {msg.pending
                      ? t("envoi")
                      : new Date(msg.created_at).toLocaleTimeString(langue() === "en" ? "en-GB" : "fr-FR", { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} className="h-4" />
        </div>

        {/* Input */}
        <div className="bg-white border-t border-light px-4 md:px-6 py-4 flex-shrink-0 mt-auto">
          {sendError && (
            <p className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-2 mb-3">{sendError}</p>
          )}
          <div className="flex items-center gap-3">
            <div className="flex-1 relative flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                maxLength={2000}
                placeholder={t("placeholder")}
                aria-label={t("votreMessage")}
                className="w-full bg-light border border-transparent focus:border-primary/20 focus:bg-white rounded-full pl-5 pr-12 py-3.5 text-sm text-dark outline-none placeholder:text-muted transition-all shadow-sm"
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim()}
              aria-label={t("envoyer")}
              className="w-12 h-12 bg-primary rounded-full flex items-center justify-center disabled:opacity-50 hover:bg-primary-600 transition-all shadow-md active:scale-95 flex-shrink-0"
            >
              <Send size={18} className="text-white ml-0.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
