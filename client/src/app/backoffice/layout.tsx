import type { Metadata } from "next";
import AdminShell from "@/components/backoffice/AdminShell";
import Document, { metadataDuSite } from "@/components/layout/Document";

// The back-office stays in French
export async function generateMetadata(): Promise<Metadata> {
  return {
    ...(await metadataDuSite("fr")),
    title: { default: "Back-office · Kwa-Ba", template: "%s · Kwa-Ba" },
    robots: { index: false, follow: false },
  };
}

export default function BackofficeLayout({ children }: { children: React.ReactNode }) {
  return (
    <Document locale="fr">
      <AdminShell>{children}</AdminShell>
    </Document>
  );
}
