"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { ClipboardList, History, Home, LayoutDashboard, LogOut, ShieldAlert, UserCheck } from "lucide-react";
import Logo from "@/components/layout/Logo";
import AlerteVerifications from "./AlerteVerifications";
import { useTableauAgent } from "../hooks";
import { useCompteursVerification } from "../compteurs";
import { cn } from "@/lib/utils";

type Compteur = "libres" | "miennes";

const NAV: { href: string; label: string; court: string; icon: typeof Home; compteur?: Compteur }[] = [
  { href: "/agent", label: "Accueil", court: "Accueil", icon: Home },
  { href: "/agent/a-faire", label: "À faire", court: "À faire", icon: ClipboardList, compteur: "libres" },
  { href: "/agent/missions", label: "Mes missions", court: "Missions", icon: UserCheck, compteur: "miennes" },
  { href: "/agent/historique", label: "Historique", court: "Historique", icon: History },
];

/**
 * Field agents' space, designed for phones (tab bar at the bottom) and usable on computers (side menu). Open to
 * agents and administrators: an administrator does everything an agent does there, and gets back to the
 * back-office through the menu. An agent never has access to the back-office (also refused by the API).
 */
export default function AgentShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const role = session?.user?.role;
  const autorise = role === "agent" || role === "admin";
  const { data: tableau } = useTableauAgent(autorise);
  const { data: compteursVerification } = useCompteursVerification(autorise);

  const totaux: Record<Compteur, number> = {
    libres: tableau?.types.reduce((n, t) => n + t.libres, 0) ?? 0,
    miennes: tableau?.types.reduce((n, t) => n + t.miennes, 0) ?? 0,
  };
  const actif = (href: string) => (href === "/agent" ? pathname === href : pathname.startsWith(href));
  // The page of a mission belongs to "My missions"
  const actifOnglet = (href: string) => actif(href) || (href === "/agent/missions" && pathname.startsWith("/agent/mission/"));
  const courant = NAV.find((n) => actifOnglet(n.href));

  if (status === "loading") return <div className="min-h-screen bg-light" />;

  // The middleware already filters; second check on the page (the API remains the only judge: 403 otherwise)
  if (!autorise) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center bg-light">
        <ShieldAlert size={40} className="text-red-600" />
        <p className="font-heading font-bold text-xl text-dark">Accès réservé aux agents de terrain</p>
        <Link href="/" className="text-primary font-bold hover:underline">Retour au site</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-light lg:flex">
      <aside className="hidden lg:flex lg:flex-col w-64 flex-shrink-0 bg-white border-r border-gray-100 sticky top-0 h-screen p-5">
        <Logo size="sm" />
        <p className="text-[11px] font-bold uppercase tracking-widest text-muted mt-2 mb-8">Espace agent</p>
        <nav className="space-y-1 flex-1" aria-label="Espace agent">
          {NAV.map(({ href, label, icon: Icon, compteur }) => (
            <Link key={href} href={href} aria-current={actifOnglet(href) ? "page" : undefined}
              className={cn("flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium",
                actifOnglet(href) ? "bg-primary/10 text-primary" : "text-dark hover:bg-gray-50")}>
              <Icon size={18} aria-hidden /> {label}
              {compteur && <Pastille nombre={totaux[compteur]} className="ml-auto" />}
            </Link>
          ))}
          {role === "admin" && (
            <Link href="/backoffice" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-dark hover:bg-gray-50 mt-4 border-t border-gray-100 pt-4">
              <LayoutDashboard size={18} aria-hidden /> Back-office
            </Link>
          )}
        </nav>
        <div className="border-t border-gray-100 pt-4">
          <p className="text-sm font-semibold text-dark truncate">{session?.user?.name}</p>
          <p className="text-xs text-muted">{role === "admin" ? "Administrateur" : "Agent de terrain"}</p>
          <button onClick={() => signOut({ callbackUrl: "/" })} className="mt-3 flex items-center gap-2 text-sm font-medium text-dark hover:text-red-600">
            <LogOut size={15} aria-hidden /> Se déconnecter
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <header className="lg:hidden sticky top-0 z-40 bg-white border-b border-gray-100">
          <div className="flex items-center justify-between gap-2 px-4 h-14">
            <div className="flex items-center gap-2 min-w-0">
              <Logo size="sm" />
              <span className="text-xs font-semibold text-muted truncate">· {courant?.label ?? "Espace agent"}</span>
            </div>
            <div className="flex items-center gap-1">
              {role === "admin" && (
                <Link href="/backoffice" aria-label="Back-office" className="w-10 h-10 rounded-full flex items-center justify-center text-dark hover:bg-gray-100">
                  <LayoutDashboard size={19} aria-hidden />
                </Link>
              )}
              <button onClick={() => signOut({ callbackUrl: "/" })} aria-label="Se déconnecter"
                className="w-10 h-10 rounded-full flex items-center justify-center text-gray-500 hover:text-red-600 hover:bg-red-50">
                <LogOut size={18} aria-hidden />
              </button>
            </div>
          </div>
        </header>

        {/* Room for the tab bar on phones */}
        <main id="contenu" tabIndex={-1} className="px-4 py-5 sm:px-6 lg:p-8 pb-28 lg:pb-8 max-w-4xl outline-none">{children}</main>

        <nav aria-label="Espace agent" className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-100 pb-[env(safe-area-inset-bottom)]">
          <ul className="grid grid-cols-4">
            {NAV.map(({ href, court, icon: Icon, compteur }) => (
              <li key={href}>
                <Link href={href} aria-current={actifOnglet(href) ? "page" : undefined}
                  className={cn("relative flex flex-col items-center gap-1 pt-2.5 pb-2 text-[11px] font-semibold",
                    actifOnglet(href) ? "text-primary" : "text-gray-500")}>
                  <span className="relative">
                    <Icon size={22} aria-hidden />
                    {compteur && <Pastille nombre={totaux[compteur]} petite className="absolute -top-1.5 -right-3" />}
                  </span>
                  {court}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <AlerteVerifications compteurs={compteursVerification} />
      </div>
    </div>
  );
}

/** Number of pending items (hidden at 0). */
function Pastille({ nombre, petite, className }: { nombre: number; petite?: boolean; className?: string }) {
  if (nombre <= 0) return null;
  return (
    <span className={cn("rounded-full bg-orange-700 text-white font-bold tabular-nums flex items-center justify-center",
      petite ? "min-w-[18px] h-[18px] px-1 text-[10px] ring-2 ring-white" : "min-w-[22px] h-[22px] px-1.5 text-xs", className)}>
      {nombre > 99 ? "99+" : nombre}
      <span className="sr-only"> en attente</span>
    </span>
  );
}
