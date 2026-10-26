"use client";

import { useTranslations } from "next-intl";
import { Mail } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Logo from "@/components/layout/Logo";
import SelecteurLangue from "@/components/layout/SelecteurLangue";
import { MentionDevise, SelecteurDevise } from "@/components/layout/Devise";
import GererCookiesBouton from "@/components/legal/GererCookiesBouton";
import { CONTACT_EMAIL } from "@/lib/contact";
import { filtrerLiens, useReglagesSite } from "@/lib/site";

const COLUMNS = [
  {
    title: "decouvrir",
    links: [
      { href: "/recherche", label: "hebergements" },
      { href: "/decouvrir", label: "experiences" },
      { href: "/recherche?sort=note", label: "mieuxNotes" },
      { href: "/transfert", label: "transfert" },
      { href: "/location", label: "location" },
      { href: "/together", label: "together" },
      { href: "/give", label: "give" },
      { href: "/concierge", label: "concierge" },
    ],
  },
  {
    title: "hotes",
    links: [
      { href: "/hote", label: "devenirHote" },
      { href: "/hote/espace", label: "espaceHote" },
    ],
  },
  {
    title: "assistance",
    links: [
      { href: "/profil/aide", label: "aide" },
      { href: "/remboursement", label: "remboursement" },
    ],
  },
];

const LEGAL = [
  { href: "/mentions-legales", label: "mentions" },
  { href: "/cgu", label: "cgu" },
  { href: "/cgv", label: "cgv" },
  { href: "/confidentialite", label: "confidentialite" },
  { href: "/cookies", label: "cookies" },
];

export default function Footer() {
  const t = useTranslations("pied");
  const reglages = useReglagesSite().data;
  return (
    <footer className="bg-white border-t border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 md:py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="col-span-2 md:col-span-1">
            <Logo />
            <p className="text-gray-600 text-sm mt-3 max-w-xs leading-relaxed">{t("accroche")}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <SelecteurLangue complet />
              <SelecteurDevise complet />
            </div>
            <MentionDevise className="mt-2" />
            <ul className="mt-4 space-y-1.5 text-sm text-gray-600" aria-label={t("contact")}>
              <li className="flex items-center gap-2">
                <Mail size={15} className="text-primary flex-shrink-0" />
                <a href={`mailto:${CONTACT_EMAIL}`} className="hover:text-primary">{CONTACT_EMAIL}</a>
              </li>
            </ul>
          </div>
          {COLUMNS.map((col) => (
            <nav key={col.title} aria-label={t(`titres.${col.title}`)}>
              <h2 className="font-heading font-bold text-dark text-sm mb-3">{t(`titres.${col.title}`)}</h2>
              <ul className="space-y-2">
                {filtrerLiens(col.links, reglages?.modules).map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className="text-sm text-gray-600 hover:text-primary transition-colors">{t(`liens.${l.label}`)}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-10 pt-6 border-t border-gray-100 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <p className="text-gray-600 text-xs">&copy; {new Date().getFullYear()} Kwa-Ba. {t("droits")}</p>
          <nav aria-label={t("informationsLegales")}>
            <ul className="flex flex-wrap gap-x-5 gap-y-2 text-xs">
              {LEGAL.map((l) => (
                <li key={l.href}><Link href={l.href} className="text-gray-600 hover:text-primary underline-offset-2 hover:underline">{t(`legal.${l.label}`)}</Link></li>
              ))}
              <li><GererCookiesBouton className="text-gray-600 hover:text-primary underline-offset-2 hover:underline" /></li>
            </ul>
          </nav>
        </div>
      </div>
    </footer>
  );
}
