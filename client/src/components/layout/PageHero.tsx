import { cn } from "@/lib/utils";

interface PageHeroProps {
  /** Small line above the title: service name with its icon. */
  surtitre: React.ReactNode;
  titre: React.ReactNode;
  sousTitre?: React.ReactNode;
  /** Photo behind the green (optional): kept discreet so that the text stays readable. */
  image?: string;
  /** Buttons, key points or figures under the text. */
  children?: React.ReactNode;
  /** Same width as a max-w-7xl page content (otherwise max-w-6xl). */
  large?: boolean;
  className?: string;
}

/** Top banner shared by the service pages (transfers, car rental, group trips, Give, experiences). */
export default function PageHero({ surtitre, titre, sousTitre, image, children, large = false, className }: PageHeroProps) {
  return (
    <section className={cn("relative overflow-hidden bg-gradient-to-br from-primary-700 to-primary-900 text-white", className)}>
      {image && (
        <div aria-hidden className="absolute inset-0 bg-cover bg-center opacity-30 mix-blend-luminosity" style={{ backgroundImage: `url('${image}')` }} />
      )}
      {/* Warm halo of the brand (rising sun of the logo) */}
      <div aria-hidden className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-accent/25 blur-3xl" />
      <div className={cn("relative mx-auto px-4 sm:px-6 py-10 sm:py-14", large ? "max-w-7xl" : "max-w-6xl")}>
        <p className="flex items-center gap-2 text-sm font-semibold text-accent [&_svg]:flex-shrink-0">{surtitre}</p>
        <h1 className="font-heading font-bold text-3xl sm:text-4xl mt-2 max-w-2xl leading-tight">{titre}</h1>
        {sousTitre && <p className="text-white/85 mt-3 max-w-xl">{sousTitre}</p>}
        {children}
      </div>
    </section>
  );
}
