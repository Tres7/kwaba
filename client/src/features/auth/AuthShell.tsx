import Logo from "@/components/layout/Logo";
import { cn } from "@/lib/utils";

interface AuthShellProps {
  image: string;
  title: string;
  subtitle: string;
  reverse?: boolean;
  children: React.ReactNode;
}

/** Shared layout of sign-in / sign-up / verification: form + visual panel (desktop). */
export default function AuthShell({ image, title, subtitle, reverse = false, children }: AuthShellProps) {
  return (
    <div className={cn("min-h-screen flex bg-white", reverse && "flex-row-reverse")}>
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url('${image}')` }} />
        <div className="absolute inset-0 bg-gradient-to-br from-primary/80 via-primary/60 to-orange-900/70" />
        <div className="relative z-10 flex flex-col justify-between p-12 h-full w-full">
          <Logo inverted />
          <div className="text-white max-w-md">
            <h2 className="font-heading font-bold text-4xl leading-tight mb-4">{title}</h2>
            <p className="text-white/85 text-base leading-relaxed">{subtitle}</p>
          </div>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-start sm:items-center justify-center px-5 py-10 sm:p-12 overflow-y-auto">
        <main id="contenu" tabIndex={-1} className="w-full max-w-[420px] outline-none">
          <Logo className="mb-8 lg:hidden" />
          {children}
        </main>
      </div>
    </div>
  );
}
