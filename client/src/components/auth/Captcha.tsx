"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { useLocale } from "next-intl";
import api from "@/lib/api";

const SCRIPT = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

interface Turnstile {
  render: (el: HTMLElement, options: Record<string, unknown>) => string;
  reset: (id: string) => void;
  remove: (id: string) => void;
}

declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

let chargement: Promise<void> | null = null;

function chargerScript(): Promise<void> {
  if (window.turnstile) return Promise.resolve();
  chargement ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      chargement = null;
      reject(new Error("Turnstile"));
    };
    document.head.appendChild(script);
  });
  return chargement;
}

export interface CaptchaHandle {
  /** New challenge (a token can only be used once: to call after every refused submission). */
  reset: () => void;
}

interface CaptchaProps {
  /** Token to send with the form, or null while the box is not validated (or after it expired). */
  onToken: (jeton: string | null) => void;
  /** Captcha active (key received): the form must wait for a token. Until it is called, nothing is required
   *  in the browser (the server refuses a missing token anyway when the captcha is active). */
  onActif?: () => void;
}

/** "I am human" box (Cloudflare Turnstile), often validated without a click. Key read from the API on load. */
const Captcha = forwardRef<CaptchaHandle, CaptchaProps>(function Captcha({ onToken, onActif }, ref) {
  const locale = useLocale();
  const zone = useRef<HTMLDivElement>(null);
  const widget = useRef<string | null>(null);
  const [indisponible, setIndisponible] = useState(false);
  // The callbacks change at every render of the parent: the widget always reads the latest version
  const rappels = useRef({ onToken, onActif });
  rappels.current = { onToken, onActif };

  useImperativeHandle(ref, () => ({
    reset: () => {
      rappels.current.onToken(null);
      if (widget.current && window.turnstile) window.turnstile.reset(widget.current);
    },
  }));

  // Public key read from the API (empty: captcha disabled); the widget is shown afterwards
  const [cle, setCle] = useState<string | null>(null);

  useEffect(() => {
    let annule = false;
    api.get<{ site_key: string }>("/v1/auth/captcha/")
      .then(({ data }) => {
        if (annule) return;
        if (data.site_key) rappels.current.onActif?.();
        setCle(data.site_key);
      })
      // API unreachable: submission is allowed, the server decides (it refuses a missing token if the captcha is active)
      .catch(() => !annule && setIndisponible(true));
    return () => { annule = true; };
  }, []);

  useEffect(() => {
    if (!cle) return;
    let annule = false;
    chargerScript()
      .then(() => {
        if (annule || !zone.current || !window.turnstile) return;
        widget.current = window.turnstile.render(zone.current, {
          sitekey: cle,
          language: locale,
          theme: "light",
          callback: (jeton: string) => rappels.current.onToken(jeton),
          "expired-callback": () => rappels.current.onToken(null),
          "error-callback": () => rappels.current.onToken(null),
        });
      })
      .catch(() => !annule && setIndisponible(true));
    return () => {
      annule = true;
      if (widget.current && window.turnstile) window.turnstile.remove(widget.current);
      widget.current = null;
    };
  }, [cle, locale]);

  if (indisponible || !cle) return null;
  return <div ref={zone} className="flex justify-center min-h-[65px]" />;
});

export default Captcha;
