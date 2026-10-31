"use client";

import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { Search, Menu, ArrowRight, LogIn, UserPlus, MessageCircle, Heart, CalendarCheck, User, LogOut, Home, ShieldCheck, Plane, Car, Users, Sparkles, HandHeart, ClipboardCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { compterNonLus } from "@/features/messaging";
import { usePolling } from "@/lib/usePolling";
import { useTranslations } from "next-intl";
import { cn, initials } from "@/lib/utils";
import Logo from "@/components/layout/Logo";
import MobileDrawer, { DrawerItem } from "@/components/layout/MobileDrawer";
import SelecteurLangue from "@/components/layout/SelecteurLangue";
import { MentionDevise, SelecteurDevise } from "@/components/layout/Devise";
import ChampDestination from "@/components/hebergement/ChampDestination";
import { filtrerLiens, useReglagesSite } from "@/lib/site";

const UNREAD_POLL_INTERVAL_MS = 10_000;

const NAV_LINKS = [
  { href: "/recherche", label: "hebergements" },
  { href: "/decouvrir", label: "experiences" },
  // Shown only on large screens (otherwise the bar overflows); always present in the mobile menu and the footer
  { href: "/transfert", label: "transferts", large: true },
  { href: "/together", label: "together", large: true },
  { href: "/give", label: "give", large: true },
  { href: "/hote", label: "devenirHote" },
];

function SearchForm({ onDone, className, focus }: { onDone?: () => void; className?: string; focus?: boolean }) {
  const router = useRouter();
  const t = useTranslations("nav");
  const [q, setQ] = useState("");
  const champ = useRef<HTMLInputElement>(null);

  // Field already present but hidden (CSS): autoFocus would not apply, the cursor is placed on opening
  useEffect(() => {
    if (focus) champ.current?.focus();
  }, [focus]);

  const aller = (ville: string) => {
    const city = ville.trim();
    router.push(city ? `/recherche?city=${encodeURIComponent(city)}` : "/recherche");
    setQ("");
    onDone?.();
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    aller(q);
  };

  return (
    <form method="post" onSubmit={submit} role="search" className={cn("relative w-full flex items-center bg-white border border-gray-200 rounded-full py-1.5 pl-4 pr-1.5 shadow-sm hover:shadow transition-shadow", className)}>
      <Search size={18} className="text-gray-400 flex-shrink-0 mr-3" />
      <ChampDestination
        type="search"
        value={q}
        onChange={setQ}
        onVille={(ville) => aller(ville)}
        onLogement={() => { setQ(""); onDone?.(); }}
        placeholder={t("rechercherVille")}
        ariaLabel={t("rechercherDestination")}
        inputRef={champ}
        className="w-full"
        inputClassName="w-full bg-transparent border-none text-base md:text-sm text-dark outline-none placeholder:text-gray-400"
        listeClassName="-left-12 -right-1.5"
      />
      <button type="submit" aria-label={t("lancerRecherche")} className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white flex-shrink-0 hover:bg-primary-600 transition-colors ml-2">
        <ArrowRight size={16} />
      </button>
    </form>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tRoles = useTranslations("roles");
  const [mobileOpen, setMobileOpen] = useState(false);
  // Screens from 1024 to 1535 px: the bar has no room for a readable search field next to the links;
  // a magnifier opens the full-width search under the bar
  const [rechercheOuverte, setRechercheOuverte] = useState(false);
  const { data: session, status } = useSession();
  const authenticated = status === "authenticated" && !!session && !session.error;

  const [unread, setUnread] = useState(0);
  const fetchUnread = useCallback(async () => {
    setUnread(await compterNonLus());
  }, []);

  // Refreshed at every page change (the badge goes down as soon as a thread is read),
  // then every 10 s and when the window gets the focus back
  useEffect(() => {
    if (!authenticated) {
      setUnread(0);
      return;
    }
    fetchUnread().catch(() => {});
  }, [authenticated, pathname, fetchUnread]);

  usePolling(fetchUnread, UNREAD_POLL_INTERVAL_MS, authenticated);

  // Closes the mobile menu at every navigation (the panel handles the scroll lock itself)
  useEffect(() => {
    setMobileOpen(false);
    setRechercheOuverte(false);
  }, [pathname]);

  const roleLabel = tRoles(session?.user?.role ?? "voyageur");
  const isHost = session?.user?.role === "hote" || session?.user?.role === "admin";
  const isAdmin = session?.user?.role === "admin";
  // Field agents' space: open to agents and administrators (served outside the language routes)
  const isAgent = session?.user?.role === "agent" || isAdmin;
  const modules = useReglagesSite().data?.modules;
  const liensBarre = filtrerLiens(NAV_LINKS, modules);
  const liensMobile = <T extends { href: string }>(liens: T[]) => filtrerLiens(liens, modules);

  const Avatar = ({ size }: { size: string }) => (
    <div className={cn("rounded-full bg-primary/10 overflow-hidden border border-primary/20 flex items-center justify-center flex-shrink-0", size)}>
      {session?.user?.image ? (
        <img src={session.user.image} alt="" className="w-full h-full object-cover" />
      ) : (
        <span className="text-primary font-bold text-sm">{initials(session?.user?.name)}</span>
      )}
    </div>
  );

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-gray-100 shadow-sm">
      <div className="max-w-7xl 2xl:max-w-[1536px] mx-auto px-4 sm:px-6 h-16 md:h-20 flex items-center justify-between gap-4 lg:gap-6">
        <Logo />

        {/* Field built into the bar only when it has room to be readable (≥ 1536 px) */}
        <div className="hidden 2xl:flex flex-1 min-w-[280px] max-w-md mx-auto">
          <SearchForm />
        </div>

        <div className="hidden md:flex items-center gap-5 lg:gap-6">
          <button
            type="button" onClick={() => setRechercheOuverte((o) => !o)}
            aria-expanded={rechercheOuverte} aria-controls="recherche-barre" aria-label={t("rechercherDestination")}
            className={cn("hidden lg:flex 2xl:hidden w-10 h-10 rounded-full items-center justify-center border transition-colors",
              rechercheOuverte ? "border-primary text-primary bg-primary/5" : "border-gray-200 text-dark hover:border-primary hover:text-primary")}
          >
            <Search size={18} />
          </button>

          <nav className="flex items-center gap-4 lg:gap-5" aria-label={t("navigationPrincipale")}>
            {liensBarre.map(({ href, label, large }) => (
              <Link
                key={href}
                href={isHost && href === "/hote" ? "/hote/espace" : href}
                className={cn("text-sm font-medium transition-colors whitespace-nowrap", large && "hidden xl:inline",
                  pathname.startsWith(href) ? "text-primary" : "text-dark hover:text-primary")}
              >
                {isHost && href === "/hote" ? t("espaceHote") : t(label)}
              </Link>
            ))}
          </nav>

          <SelecteurLangue />
          <SelecteurDevise />

          <div className="w-px h-6 bg-gray-200" />

          <div className="flex items-center gap-3">
            {authenticated ? (
              <>
                {isAgent && (
                  <Link href="/agent" className="flex items-center gap-1.5 text-xs font-bold text-white bg-primary rounded-full px-3 py-1.5 hover:bg-primary/90 whitespace-nowrap">
                    <ClipboardCheck size={14} /> {t("espaceAgent")}
                  </Link>
                )}
                {isAdmin && (
                  <Link href="/backoffice" className="flex items-center gap-1.5 text-xs font-bold text-dark border border-gray-200 rounded-full px-3 py-1.5 hover:border-primary hover:text-primary">
                    <ShieldCheck size={14} /> Back-office
                  </Link>
                )}
                <Link href="/messages" className="relative p-2 text-gray-500 hover:text-primary transition-colors" aria-label={unread ? t("messagesNonLus", { nombre: unread }) : t("messages")}>
                  <MessageCircle size={20} />
                  {unread > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center border-2 border-white">
                      {unread > 9 ? "9+" : unread}
                    </span>
                  )}
                </Link>
                <Link href="/profil" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                  <div className="text-right hidden xl:block">
                    <p className="text-xs font-bold text-dark leading-tight max-w-[140px] truncate">{session.user?.name ?? t("monProfil")}</p>
                    <p className="text-[10px] text-gray-500">{roleLabel}</p>
                  </div>
                  <Avatar size="w-9 h-9" />
                </Link>
              </>
            ) : status !== "loading" ? (
              <>
                <Link href={`/login?callbackUrl=${encodeURIComponent(pathname)}`} className="flex items-center gap-1.5 text-sm font-medium text-dark hover:text-primary transition-colors whitespace-nowrap">
                  <LogIn size={16} />
                  {t("seConnecter")}
                </Link>
                <Link href="/register" className="flex items-center gap-1.5 bg-primary text-white text-sm font-bold px-4 py-2 rounded-full hover:bg-primary/90 transition-colors shadow-sm whitespace-nowrap">
                  <UserPlus size={15} />
                  {t("sInscrire")}
                </Link>
              </>
            ) : (
              <div className="w-24 h-9 rounded-full skeleton" />
            )}
          </div>
        </div>

        <div className="flex md:hidden items-center gap-1">
          {authenticated && (
            <Link href="/messages" className="relative zone-tactile p-2 text-dark" aria-label={t("messages")}>
              <MessageCircle size={22} />
              {unread > 0 && <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white" />}
            </Link>
          )}
          <button className="relative zone-tactile p-2 text-dark" onClick={() => setMobileOpen(true)} aria-expanded={mobileOpen} aria-haspopup="dialog" aria-label={t("ouvrirMenu")}>
            <Menu size={24} />
          </button>
        </div>
      </div>

      {/* Search under the bar: always on tablets, on demand (magnifier) from 1024 to 1535 px */}
      <div id="recherche-barre" className={cn("hidden md:block lg:hidden px-6 pb-3", rechercheOuverte && "lg:block 2xl:hidden")}>
        <div className="max-w-2xl mx-auto">
          <SearchForm focus={rechercheOuverte} onDone={() => setRechercheOuverte(false)} />
        </div>
      </div>

      <MobileDrawer open={mobileOpen} onClose={() => setMobileOpen(false)} label={t("menu")} header={<Logo size="sm" />}>
        <DrawerItem>
          <SearchForm onDone={() => setMobileOpen(false)} className="bg-gray-50" />
        </DrawerItem>

        {authenticated && (
          <DrawerItem className="mt-5">
            <Link href="/profil" className="flex items-center gap-3 p-3 rounded-2xl bg-light-muted">
              <Avatar size="w-11 h-11" />
              <div className="min-w-0">
                <p className="text-sm font-bold text-dark truncate">{session.user?.name ?? t("monProfil")}</p>
                <p className="text-xs text-gray-500">{roleLabel}</p>
              </div>
            </Link>
          </DrawerItem>
        )}

        {/* Agents come here to work: their space at the top of the menu */}
        {isAgent && (
          <DrawerItem className="mt-3">
            <Link href="/agent" onClick={() => setMobileOpen(false)}
              className="flex items-center justify-center gap-2 py-3 rounded-xl bg-primary text-white text-[15px] font-bold">
              <ClipboardCheck size={18} /> {t("espaceAgent")}
            </Link>
          </DrawerItem>
        )}

        <nav className="mt-4 space-y-1" aria-label={t("navigationMobile")}>
          {liensMobile([
            { href: "/", label: t("accueil"), icon: Home },
            { href: "/recherche", label: t("hebergements"), icon: Search },
            { href: "/decouvrir", label: t("experiences"), icon: ArrowRight },
            { href: "/transfert", label: t("transfertAeroport"), icon: Plane },
            { href: "/location", label: t("location"), icon: Car },
            { href: "/together", label: t("voyagerAPlusieurs"), icon: Users },
            { href: "/concierge", label: t("conciergeIA"), icon: Sparkles },
            { href: "/give", label: t("faireUnDon"), icon: HandHeart },
            ...(authenticated
              ? [
                  { href: "/profil/reservations", label: t("mesReservations"), icon: CalendarCheck },
                  { href: "/favoris", label: t("mesFavoris"), icon: Heart },
                  { href: "/messages", label: unread ? `${t("messages")} (${unread})` : t("messages"), icon: MessageCircle },
                  { href: "/profil", label: t("monProfil"), icon: User },
                ]
              : []),
            { href: isHost ? "/hote/espace" : "/hote", label: isHost ? t("espaceHote") : t("devenirHote"), icon: Home },
            ...(isAdmin ? [{ href: "/backoffice", label: "Back-office", icon: ShieldCheck }] : []),
          ]).map(({ href, label, icon: Icon }) => (
            <DrawerItem key={href + label}>
              <Link
                href={href}
                onClick={() => setMobileOpen(false)}
                className={cn("flex items-center gap-3 px-3 py-3 rounded-xl text-[15px] font-medium transition-colors", pathname === href ? "bg-primary/10 text-primary" : "text-dark hover:bg-gray-50")}
              >
                <Icon size={18} className="text-primary" />
                {label}
              </Link>
            </DrawerItem>
          ))}
        </nav>

        <DrawerItem className="mt-4 flex flex-wrap gap-2">
          <SelecteurLangue complet />
          <SelecteurDevise complet />
          <MentionDevise className="w-full" />
        </DrawerItem>

        <DrawerItem className="mt-4 pt-4 border-t border-gray-100">
          {authenticated ? (
            <button onClick={() => signOut({ callbackUrl: "/" })} className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-red-100 text-red-600 text-sm font-bold">
              <LogOut size={16} /> {t("seDeconnecter")}
            </button>
          ) : (
            <div className="flex flex-col gap-3">
              <Link href={`/login?callbackUrl=${encodeURIComponent(pathname)}`} onClick={() => setMobileOpen(false)} className="w-full text-center py-3 rounded-xl border border-gray-200 text-sm font-bold text-dark hover:bg-gray-50 transition-colors">
                {t("seConnecter")}
              </Link>
              <Link href="/register" onClick={() => setMobileOpen(false)} className="w-full text-center py-3 rounded-xl bg-primary text-white text-sm font-bold hover:bg-primary/90 transition-colors">
                {t("creerCompte")}
              </Link>
            </div>
          )}
        </DrawerItem>
      </MobileDrawer>
    </header>
  );
}
