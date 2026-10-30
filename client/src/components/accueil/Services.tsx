"use client";

import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { motion, type Variants } from "framer-motion";
import { AirplaneTiltIcon, ArrowRightIcon, CarProfileIcon, CompassIcon, HandHeartIcon, SparkleIcon, UsersThreeIcon, type Icon } from "@phosphor-icons/react";
import { useLiensVisibles } from "@/lib/site";

const SERVICES: { href: string; cle: string; Icone: Icon }[] = [
  { href: "/transfert", cle: "transfert", Icone: AirplaneTiltIcon },
  { href: "/location", cle: "location", Icone: CarProfileIcon },
  { href: "/decouvrir", cle: "experiences", Icone: CompassIcon },
  { href: "/together", cle: "together", Icone: UsersThreeIcon },
  { href: "/concierge", cle: "concierge", Icone: SparkleIcon },
  { href: "/give", cle: "give", Icone: HandHeartIcon },
];

const carte: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

/** Home: the other Kwa-Ba services, without those whose module is hidden. */
export default function Services() {
  const t = useTranslations("accueil.services");
  const services = useLiensVisibles(SERVICES);

  return (
    <section aria-labelledby="services-titre">
      <div className="mb-6 md:mb-8 max-w-2xl">
        <h2 id="services-titre" className="font-heading font-bold text-dark text-2xl md:text-3xl">{t("titre")}</h2>
        <p className="text-gray-500 text-sm mt-1">{t("texte")}</p>
      </div>
      <motion.ul
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5"
        initial="hidden" whileInView="show" viewport={{ once: true, margin: "-60px" }}
        transition={{ staggerChildren: 0.06 }}
      >
        {services.map(({ href, cle, Icone }) => (
          <motion.li key={href} variants={carte}>
            {/* Phones: compact rows (icon beside the text); larger screens: cards */}
            <Link
              href={href}
              className="group h-full flex items-start gap-4 sm:flex-col sm:items-stretch sm:gap-0 rounded-2xl p-4 sm:p-5 md:p-6 bg-white border border-gray-100 shadow-sm hover:shadow-card hover:border-primary/20 transition-all"
            >
              <span className="h-12 w-12 flex-shrink-0 rounded-xl flex items-center justify-center sm:mb-4 bg-primary-50 text-primary">
                <Icone size={26} weight="duotone" aria-hidden />
              </span>
              <span className="flex flex-col min-w-0">
                <span className="font-heading font-bold text-base sm:text-lg text-dark">{t(`${cle}.titre`)}</span>
                <span className="text-sm leading-relaxed mt-1 sm:mt-1.5 text-gray-600">{t(`${cle}.texte`)}</span>
              </span>
              <span className="mt-auto pt-4 hidden sm:inline-flex items-center gap-1.5 text-sm font-bold text-primary">
                {t("decouvrir")} <ArrowRightIcon size={16} weight="bold" className="transition-transform group-hover:translate-x-1" aria-hidden />
              </span>
            </Link>
          </motion.li>
        ))}
      </motion.ul>
    </section>
  );
}
