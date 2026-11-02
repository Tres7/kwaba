"use client";

import { useRouter } from "@/i18n/navigation";
import { signIn } from "next-auth/react";
import { useTranslations } from "next-intl";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

let chargement: Promise<void> | null = null;
function chargerScriptGoogle(): Promise<void> {
  if (window.google) return Promise.resolve();
  if (!chargement) {
    chargement = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => { chargement = null; reject(new Error("script Google indisponible")); };
      document.head.appendChild(s);
    });
  }
  return chargement;
}

interface GoogleButtonProps {
  label: string;
  callbackUrl: string;
  onError: (message: string) => void;
}

/** Google Identity Services button. Hidden if NEXT_PUBLIC_GOOGLE_CLIENT_ID is not configured. */
export default function GoogleButton({ label, callbackUrl, onError }: GoogleButtonProps) {
  const router = useRouter();
  const t = useTranslations("auth");

  if (!GOOGLE_CLIENT_ID) return null;

  const handleClick = async () => {
    onError("");
    // The Google script is only loaded on click: no request to Google for visitors who do not use it
    try {
      await chargerScriptGoogle();
    } catch {
      onError(t("googleIndisponible"));
      return;
    }
    if (!window.google) {
      onError(t("googleIndisponible"));
      return;
    }

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        if (!response.credential) {
          onError(t("googleJeton"));
          return;
        }
        try {
          const res = await signIn("google-id-token", { redirect: false, idToken: response.credential });
          if (res?.error) {
            const messages: Record<string, string> = {
              inactive: t("desactive"),
              too_many_attempts: t("tropDeTentatives"),
              serveur: t("serveurInjoignable"),
            };
            onError(messages[res.code ?? ""] ?? t("googleRefus"));
            return;
          }
          router.push(callbackUrl);
          router.refresh();
        } catch {
          onError(t("serveurInjoignable"));
        }
      },
    });
    window.google.accounts.id.prompt();
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className="w-full flex items-center justify-center gap-3 bg-white border border-gray-200 rounded-2xl py-3.5 text-sm font-medium text-dark hover:bg-gray-50 transition-colors shadow-sm"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        {label}
      </button>
      <div className="flex items-center gap-4 my-6">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="text-gray-400 text-xs font-medium">{t("ouParEmail")}</span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>
    </>
  );
}
