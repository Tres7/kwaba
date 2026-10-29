"use client";

import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { motion, type Variants } from "framer-motion";
import { AirplaneTiltIcon, ArrowRightIcon, CarProfileIcon, CompassIcon, HandHeartIcon, SparkleIcon, UsersThreeIcon, type Icon } from "@phosphor-icons/react";
import { useLiensVisibles } from "@/lib/site";
import { cn } from "@/lib/utils";

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

/** Home: the other Kwa-Ba services, without those whose module is hidden. The transfer, most asked for, stands out. */
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
        {services.map(({ href, cle, Icone }, i) => {
          const vedette = i === 0;
          return (
            <motion.li key={href} variants={carte}>
              <Link
                href={href}
                className={cn(
                  // Phones: compact rows (icon beside the text); larger screens: cards
                  "group relative h-full flex items-start gap-4 sm:flex-col sm:items-stretch sm:gap-0 rounded-2xl p-4 sm:p-5 md:p-6 overflow-hidden transition-all",
                  vedette
                    ? "bg-gradient-to-br from-primary-700 to-primary-900 text-white shadow-card hover:shadow-card-hover"
                    : "bg-white border border-gray-100 shadow-sm hover:shadow-card hover:border-primary/20",
                )}
              >
                {vedette && <span aria-hidden className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-accent/25 blur-3xl" />}
                <span className={cn("relative h-12 w-12 flex-shrink-0 rounded-xl flex items-center justify-center sm:mb-4",
                  vedette ? "bg-white/10 text-accent" : "bg-primary-50 text-primary")}>
                  <Icone size={26} weight="duotone" aria-hidden />
                </span>
                <span className="relative flex flex-col min-w-0">
                  <span className={cn("font-heading font-bold text-base sm:text-lg", !vedette && "text-dark")}>{t(`${cle}.titre`)}</span>
                  <span className={cn("text-sm leading-relaxed mt-1 sm:mt-1.5", vedette ? "text-white/85 max-w-sm" : "text-gray-600")}>{t(`${cle}.texte`)}</span>
                </span>
                <span className={cn("relative mt-auto pt-4 hidden sm:inline-flex items-center gap-1.5 text-sm font-bold",
                  vedette ? "text-accent" : "text-primary")}>
                  {t("decouvrir")} <ArrowRightIcon size={16} weight="bold" className="transition-transform group-hover:translate-x-1" aria-hidden />
                </span>
              </Link>
            </motion.li>
          );
        })}
      </motion.ul>
    </section>
  );
}
