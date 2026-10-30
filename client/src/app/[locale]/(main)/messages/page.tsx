"use client";

import { useCallback, useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFormat } from "@/lib/format";
import api from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import type { MessagingConversation } from "@/types/api/messaging";
import { useTranslations } from "next-intl";

const LIST_POLL_INTERVAL_MS = 10_000;

function formatTime(iso: string, { formatDate, langue }: ReturnType<typeof useFormat>) {
  const date = new Date(iso);
  const isToday = date.toDateString() === new Date().toDateString();
  return isToday
    ? date.toLocaleTimeString(langue() === "en" ? "en-GB" : "fr-FR", { hour: "2-digit", minute: "2-digit" })
    : formatDate(iso, { day: "numeric", month: "short" });
}

export default function MessagesPage() {
  const t = useTranslations("messages");
  const format = useFormat();
  const [conversations, setConversations] = useState<MessagingConversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchConversations = useCallback(async () => {
    const res = await api.get("/v1/messaging/conversations/");
    setConversations(res.data.results);
    setError(false);
  }, []);

  useEffect(() => {
    fetchConversations()
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [fetchConversations]);

  usePolling(fetchConversations, LIST_POLL_INTERVAL_MS, !loading);

  return (
    <div className="min-h-screen bg-light">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="font-heading font-bold text-dark text-2xl sm:text-3xl mb-8">{t("titre")}</h1>

        {loading ? (
          <p className="text-muted text-center py-16">{t("chargement")}</p>
        ) : error ? (
          <p className="text-muted text-center py-16">{t("erreurChargement")}</p>
        ) : conversations.length === 0 ? (
          <div className="bg-white rounded-3xl shadow-card p-10 sm:p-16 flex flex-col items-center gap-4 border border-light text-center">
            <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-2">
              <MessageCircle size={36} className="text-primary" />
            </div>
            <p className="text-dark font-heading font-bold text-xl">{t("aucune")}</p>
            <p className="text-muted text-base">{t("aucuneTexte")}</p>
            <Link href="/recherche" className="mt-4 bg-primary text-white font-heading font-semibold px-8 py-3.5 rounded-xl hover:bg-primary-600 transition-colors shadow-md hover:shadow-lg hover:-translate-y-0.5">
              {t("explorer")}
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => {
              const other = conv.other_participant;
              const name = other ? `${other.first_name} ${other.last_name}`.trim() : "Utilisateur";
              const unread = conv.unread_count > 0;
              return (
                <Link
                  key={conv.id}
                  href={`/messages/${conv.id}`}
                  className="group flex items-center gap-5 bg-white rounded-2xl p-5 hover:bg-light/40 transition-all duration-300 border border-transparent hover:border-light"
                >
                  <div className="relative flex-shrink-0">
                    <div className="w-16 h-16 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center shadow-soft overflow-hidden">
                      {other?.avatar_url ? (
                        <img src={other.avatar_url} alt={name} className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-white font-heading font-bold text-xl">{name[0]}</span>
                      )}
                    </div>
                    {unread && (
                      <span className="absolute -top-1 -right-1 min-w-6 h-6 px-1.5 bg-primary text-white text-xs font-bold rounded-full border-2 border-white flex items-center justify-center">
                        {conv.unread_count > 9 ? "9+" : conv.unread_count}
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-baseline mb-1 gap-3">
                      <p className="font-heading font-bold text-dark text-lg truncate group-hover:text-primary transition-colors">
                        {name}
                        <span className="ml-2 text-xs font-medium text-muted">{conv.my_role === "host" ? t("voyageur") : t("hote")}</span>
                      </p>
                      <p className="text-muted text-xs font-medium flex-shrink-0">{formatTime(conv.last_message_at, format)}</p>
                    </div>
                    <p className="text-primary text-sm font-medium mb-1 truncate">{conv.hebergement?.name ?? t("supprime")}</p>
                    <p className={cn("text-sm truncate", unread ? "text-dark font-semibold" : "text-muted")}>
                      {conv.last_message
                        ? `${conv.last_message.is_own ? t("vous") : ""}${conv.last_message.content}`
                        : t("aucunMessage")}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
