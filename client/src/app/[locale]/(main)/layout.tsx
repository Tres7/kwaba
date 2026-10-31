import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import BoutonConcierge from "@/features/concierge/BoutonConcierge";
import BientotDisponible from "@/components/lancement/BientotDisponible";
import BandeauOuverture from "@/components/lancement/BandeauOuverture";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-light flex flex-col">
      <BandeauOuverture />
      <Navbar />
      <main id="contenu" tabIndex={-1} className="flex-1 outline-none">{children}</main>
      <Footer />
      <BoutonConcierge />
      <BientotDisponible />
    </div>
  );
}
