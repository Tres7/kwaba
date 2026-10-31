"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { motion, type Variants } from "framer-motion";
import { Search, MapPin, ChevronRight, Check } from "lucide-react";
import { ArrowCounterClockwiseIcon, BackpackIcon, BedIcon, BuildingApartmentIcon, ChatsCircleIcon, ClockCountdownIcon, HouseLineIcon, LightningIcon, SealCheckIcon, ShieldCheckIcon, UsersThreeIcon, WalletIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import api from "@/lib/api";
import DateRangeField from "@/components/ui/DateRangeField";
import GuestsField from "@/components/ui/GuestsField";
import PropertyCard from "@/components/hebergement/PropertyCard";
import ChampDestination from "@/components/hebergement/ChampDestination";
import Services from "@/components/accueil/Services";
import AvisVoyageurs from "@/features/avis/AvisVoyageurs";
import type { City, Hebergement, Paginated } from "@/types/api/models";
import { useFormat } from "@/lib/format";

// Slideshow photos (public/accueil): 1240 × 1550 portrait cropped on the subject for phones, 2560 px from
// tablets, 3840 px on large screens (2xl). Classes written in full so that Tailwind generates them; the
// browser only downloads the image of the current screen size. ?v=: to increase when a photo changes its
// content under the same name (images are cached 7 days by browsers).
const heroImages = [
  "bg-[url('/accueil/hero-1-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-1.jpg?v=2')] 2xl:bg-[url('/accueil/hero-1-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-2-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-2.jpg?v=2')] 2xl:bg-[url('/accueil/hero-2-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-3-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-3.jpg?v=2')] 2xl:bg-[url('/accueil/hero-3-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-4-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-4.jpg?v=2')] 2xl:bg-[url('/accueil/hero-4-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-5-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-5.jpg?v=2')] 2xl:bg-[url('/accueil/hero-5-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-6-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-6.jpg?v=2')] 2xl:bg-[url('/accueil/hero-6-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-7-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-7.jpg?v=2')] 2xl:bg-[url('/accueil/hero-7-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-8-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-8.jpg?v=2')] 2xl:bg-[url('/accueil/hero-8-4k.jpg?v=2')]",
  "bg-[url('/accueil/hero-9-mobile.jpg?v=2')] md:bg-[url('/accueil/hero-9.jpg?v=2')] 2xl:bg-[url('/accueil/hero-9-4k.jpg?v=2')]",
];

const CATEGORIES = [
  { type: "hotel", label: "hotels", icon: BedIcon },
  { type: "appartement", label: "appartements", icon: BuildingApartmentIcon },
  { type: "villa", label: "villas", icon: HouseLineIcon },
  { type: "auberge", label: "auberges", icon: BackpackIcon },
];

const FEATURES = [
  // Kwa-Ba brand colours: green, amber, orange, slate
  { title: "paiement", icon: WalletIcon, color: "text-primary ring-primary/20" },
  { title: "instantanee", icon: LightningIcon, color: "text-secondary ring-secondary/20" },
  { title: "contact", icon: ChatsCircleIcon, color: "text-accent ring-accent/30" },
  { title: "annulation", icon: ArrowCounterClockwiseIcon, color: "text-dark ring-dark/15" },
];

const GARANTIES = [
  { title: "verifies", icon: SealCheckIcon, color: "text-primary ring-primary/20" },
  { title: "garantie", icon: ShieldCheckIcon, color: "text-secondary ring-secondary/20" },
  { title: "equipe", icon: UsersThreeIcon, color: "text-accent ring-accent/30" },
  { title: "versement", icon: ClockCountdownIcon, color: "text-dark ring-dark/15" },
];

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

const containerVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

function HeroSearch() {
  const router = useRouter();
  const t = useTranslations("accueil");
  const [city, setCity] = useState("");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [guests, setGuests] = useState(2);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (city.trim()) params.set("city", city.trim());
    if (checkIn && checkOut) {
      params.set("check_in", checkIn);
      params.set("check_out", checkOut);
    }
    params.set("guests", String(guests));
    router.push(`/recherche?${params.toString()}`);
  };

  const fieldClass = "flex-1 px-5 py-3 w-full text-left min-w-0";
  const labelClass = "block text-[11px] font-bold text-dark uppercase tracking-wide";
  const inputClass = "w-full text-base md:text-sm font-medium text-dark outline-none bg-transparent placeholder:text-gray-400";

  return (
    <form method="post"
      onSubmit={submit}
      className="animate-fade-up-delay-2 bg-white rounded-3xl md:rounded-full p-2 max-w-4xl mx-auto shadow-card flex flex-col md:flex-row md:items-center divide-y md:divide-y-0 md:divide-x divide-gray-100"
    >
      <label className={fieldClass}>
        <span className={labelClass}>{t("destination")}</span>
        <span className="flex items-center gap-2 mt-1">
          <MapPin size={16} className="text-primary flex-shrink-0" />
          <ChampDestination
            value={city} onChange={setCity} onVille={setCity}
            placeholder={t("ouAllezVous")} ariaLabel={t("destination")}
            className="flex-1 min-w-0" inputClassName={inputClass} listeClassName="-left-12 w-[min(22rem,calc(100vw-3rem))]"
          />
        </span>
      </label>
      <DateRangeField
        variant="hero" checkIn={checkIn} checkOut={checkOut}
        onChange={(a, d) => { setCheckIn(a); setCheckOut(d); }}
        className="md:flex-[1.6] min-w-0"
      />
      <div className="flex items-center justify-between gap-3 pl-5 pr-2 py-2 md:py-0 w-full md:w-auto md:flex-1">
        <div className="min-w-0 flex-1 text-left">
          <span className={labelClass}>{t("voyageurs")}</span>
          <GuestsField variant="bare" value={guests} onChange={setGuests} className="mt-1" />
        </div>
        <button type="submit" className="bg-primary hover:bg-primary-600 text-white p-4 rounded-full transition-colors flex items-center gap-2 font-bold text-sm shadow-md flex-shrink-0" aria-label={t("rechercher")}>
          <Search size={18} />
          <span className="hidden lg:inline">{t("rechercher")}</span>
        </button>
      </div>
    </form>
  );
}

function WelcomeToast() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const t = useTranslations("accueil");
  useEffect(() => {
    if (searchParams.get("bienvenue") === "1") {
      toast.success(t("bienvenue"));
      router.replace("/");
    }
  }, [searchParams, router, t]);
  return null;
}

export default function HomePage() {
  const { formatPrice } = useFormat();
  // Displayed and previous photo (kept during the fade); no previous one before the first change
  const [{ currentBg, previousBg }, setDiaporama] = useState({ currentBg: 0, previousBg: -1 });
  const { status } = useSession();
  const t = useTranslations("accueil");

  useEffect(() => {
    const interval = setInterval(
      () => setDiaporama(({ currentBg: c }) => ({ currentBg: (c + 1) % heroImages.length, previousBg: c })),
      12000,
    );
    return () => clearInterval(interval);
  }, []);

  const { data: cities = [], isLoading: citiesLoading } = useQuery({
    queryKey: ["villes"],
    queryFn: async () => (await api.get<{ results: City[] }>("/v1/hebergements/villes/")).data.results,
  });

  const { data: recommended = [], isLoading: recoLoading } = useQuery({
    queryKey: ["hebergements", "recommandes", status],
    queryFn: async () => (await api.get<Paginated<Hebergement>>("/v1/hebergements/", { params: { sort: "note", limit: 8 } })).data.results,
    enabled: status !== "loading",
  });

  return (
    <div className="bg-white min-h-screen">
      <Suspense><WelcomeToast /></Suspense>

      <section className="relative pt-16 pb-36 md:pt-28 md:pb-48 px-4 sm:px-6 text-white min-h-[560px] md:min-h-[620px] flex items-center justify-center overflow-hidden">
        {heroImages.map((img, i) => {
          // Only the displayed photo, the previous one (fading out) and the next one (preloaded) are in the page:
          // the others are only downloaded when their turn comes
          const n = heroImages.length;
          if (i !== currentBg && i !== (currentBg + 1) % n && i !== previousBg) return null;
          return (
            <div
              key={i}
              className={`absolute inset-0 z-0 bg-cover bg-center bg-no-repeat transition-opacity duration-1000 ${img} ${i === currentBg || i === previousBg ? "animate-ken-burns" : ""}`}
              style={{ opacity: i === currentBg ? 1 : 0 }}
            />
          );
        })}
        <div className="absolute inset-0 z-[1] bg-dark/45" />
        <div className="absolute bottom-0 left-0 right-0 h-40 md:h-52 bg-gradient-to-b from-transparent to-white z-[2]" />

        <div className="w-full max-w-5xl mx-auto text-center relative z-10">
          <h1 className="animate-fade-up font-heading font-bold text-4xl sm:text-5xl md:text-6xl lg:text-7xl leading-tight mb-4 drop-shadow-md">
            {t.rich("titre", { br: () => <br /> })}
          </h1>
          <p className="animate-fade-up-delay-1 text-white/90 text-base sm:text-lg md:text-xl mb-8 md:mb-12 max-w-2xl mx-auto font-medium drop-shadow">
            {t("sousTitre")}
          </p>
          <HeroSearch />
          <ul className="animate-fade-up-delay-2 mt-5 md:mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm font-medium text-white/95 drop-shadow">
            {(["verifies", "paiement", "prix"] as const).map((cle) => (
              <li key={cle} className="flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center"><Check size={13} strokeWidth={3} aria-hidden /></span>
                {t(`confiance.${cle}`)}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 pb-16 space-y-16 md:space-y-20 -mt-16 md:-mt-20 relative z-20">
        {/* Hidden while no listing is published (no empty block); shows again with the first one */}
        {(citiesLoading || cities.length > 0) && (
        <section>
          <div className="flex items-end justify-between mb-6 md:mb-8 gap-4">
            <div>
              <h2 className="font-heading font-bold text-dark text-2xl md:text-3xl">{t("destinationsPopulaires")}</h2>
              <p className="text-gray-500 text-sm mt-1">{t("destinationsTexte")}</p>
            </div>
            <Link href="/recherche" aria-label={t("voirDestinations")} className="relative zone-tactile flex items-center gap-1 text-primary text-sm font-bold hover:underline flex-shrink-0">
              {t("voirTout")} <ChevronRight size={16} />
            </Link>
          </div>
          {citiesLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
              {[0, 1, 2, 3].map((i) => <div key={i} className="h-44 md:h-64 rounded-[2rem] skeleton" />)}
            </div>
          ) : (
            <motion.div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6" variants={containerVariants} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-60px" }}>
              {cities.slice(0, 4).map((dest) => (
                <motion.div key={dest.city} variants={cardVariants}>
                  <Link href={`/recherche?city=${encodeURIComponent(dest.city)}`} className="block relative h-44 md:h-64 rounded-[2rem] overflow-hidden group shadow-sm bg-slate-200">
                    <div className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110" style={{ backgroundImage: `url('${dest.image_url}')` }} />
                    <div className="absolute inset-0 bg-gradient-to-t from-dark/80 via-dark/20 to-transparent" />
                    <div className="absolute bottom-4 left-4 right-4 md:bottom-6 md:left-6 md:right-6">
                      <h3 className="text-white font-heading font-bold text-base md:text-lg leading-tight">{dest.city}</h3>
                      <p className="text-white/80 text-xs mt-1 font-medium">
                        {t("villeResume", { nombre: dest.count, prix: formatPrice(dest.min_price) })}
                      </p>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </motion.div>
          )}
        </section>
        )}

        <section className="grid grid-cols-2 sm:flex sm:flex-wrap sm:justify-center items-center gap-3 md:gap-4" aria-label={t("typesHebergement")}>
          {CATEGORIES.map(({ type, label, icon: Icon }) => (
            <Link
              key={type}
              href={`/recherche?type=${type}`}
              className="bg-white px-4 md:px-6 py-3 md:py-4 rounded-full border border-gray-100 shadow-sm flex items-center gap-3 hover:border-primary/40 hover:shadow transition-all"
            >
              <span className="h-10 w-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-primary-50 text-primary"><Icon size={24} weight="duotone" aria-hidden /></span>
              <span className="font-bold text-dark text-sm">{t(`types.${label}`)}</span>
            </Link>
          ))}
        </section>

        {(recoLoading || recommended.length > 0) && (
        <section>
          <div className="flex items-end justify-between mb-6 md:mb-8 gap-4">
            <h2 className="font-heading font-bold text-dark text-2xl md:text-3xl">{t("mieuxNotes")}</h2>
            <Link href="/recherche?sort=note" aria-label={t("voirMieuxNotes")} className="relative zone-tactile flex items-center gap-1 text-primary text-sm font-bold hover:underline flex-shrink-0">
              {t("voirTout")} <ChevronRight size={16} />
            </Link>
          </div>
          {recoLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[0, 1, 2, 3].map((i) => <div key={i} className="h-72 rounded-2xl skeleton" />)}
            </div>
          ) : (
            // Phones: a row to swipe instead of 8 cards one under the other
            <div className="flex sm:grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 overflow-x-auto sm:overflow-visible snap-x snap-mandatory scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0 pb-2 sm:pb-0">
              {recommended.map((prop) => (
                <div key={prop.id} className="w-[82%] flex-shrink-0 snap-start sm:w-auto">
                  <PropertyCard property={prop} />
                </div>
              ))}
            </div>
          )}
        </section>
        )}

        <Services />

        <AvisVoyageurs hebergements={recommended} />

        <section className="py-12 bg-white rounded-[2rem] md:rounded-[3rem] px-6 md:px-8 text-center">
          <h2 className="font-heading font-bold text-dark text-2xl md:text-3xl mb-3">{t("pourquoi")}</h2>
          <p className="text-gray-500 max-w-2xl mx-auto text-sm mb-10 md:mb-16">
            {t("pourquoiTexte")}
          </p>
          <motion.div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8" variants={containerVariants} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-40px" }}>
            {FEATURES.map((feat) => (
              <motion.div key={feat.title} variants={cardVariants} className="flex flex-col items-center text-center">
                <div className={`w-16 h-16 md:w-20 md:h-20 rounded-2xl bg-white ring-1 shadow-sm flex items-center justify-center mb-4 md:mb-6 ${feat.color}`}>
                  <feat.icon className="w-9 h-9 md:w-11 md:h-11" weight="duotone" aria-hidden />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">{t(`atouts.${feat.title}.titre`)}</h3>
                <p className="text-gray-500 text-sm leading-relaxed max-w-[240px]">{t(`atouts.${feat.title}.texte`)}</p>
              </motion.div>
            ))}
          </motion.div>
          <motion.div className="mt-12 md:mt-16 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8" variants={containerVariants} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-40px" }}>
            {GARANTIES.map((garantie) => (
              <motion.div key={garantie.title} variants={cardVariants} className="flex flex-col items-center text-center">
                <div className={`w-16 h-16 md:w-20 md:h-20 rounded-2xl bg-white ring-1 shadow-sm flex items-center justify-center mb-4 md:mb-6 ${garantie.color}`}>
                  <garantie.icon className="w-9 h-9 md:w-11 md:h-11" weight="duotone" aria-hidden />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">{t(`garanties.${garantie.title}.titre`)}</h3>
                <p className="text-gray-500 text-sm leading-relaxed max-w-[240px]">{t(`garanties.${garantie.title}.texte`)}</p>
              </motion.div>
            ))}
          </motion.div>
        </section>
      </div>

      <section className="relative overflow-hidden bg-primary-900 py-14 md:py-20 px-4 sm:px-6">
        <div aria-hidden className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1613490493576-7fde63acd811?q=80&w=2000&auto=format&fit=crop')" }} />
        <div aria-hidden className="absolute inset-0 bg-gradient-to-r from-primary-900 via-primary-900/90 to-primary-900/50" />
        <div className="relative max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8 text-center md:text-left">
          <div className="text-white max-w-xl selection:bg-white selection:text-primary">
            <h2 className="font-heading font-bold text-3xl md:text-4xl mb-4">{t("devenezHote")}</h2>
            <p className="text-white/90 text-sm md:text-base leading-relaxed">
              {t("devenezHoteTexte")}
            </p>
            <ul className="mt-6 flex flex-wrap justify-center md:justify-start gap-x-5 gap-y-2 text-sm font-semibold">
              {(["gratuit", "agent", "versement"] as const).map((cle) => (
                <li key={cle} className="flex items-center gap-1.5"><Check size={16} strokeWidth={3} className="text-accent" aria-hidden /> {t(`hoteChiffres.${cle}`)}</li>
              ))}
            </ul>
          </div>
          <Link href="/hote" className="bg-white text-primary hover:bg-gray-50 px-8 py-4 rounded-full font-bold transition-colors shadow-lg flex-shrink-0">
            {t("commencer")}
          </Link>
        </div>
      </section>
    </div>
  );
}
