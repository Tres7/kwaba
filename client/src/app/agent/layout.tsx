import type { Metadata } from "next";
import Document, { metadataDuSite } from "@/components/layout/Document";
import AgentShell from "@/features/verifications/admin/AgentShell";

// Field agents' space: in French, never indexed
export async function generateMetadata(): Promise<Metadata> {
  return {
    ...(await metadataDuSite("fr")),
    title: { default: "Espace agent · Kwa-Ba", template: "%s · Espace agent · Kwa-Ba" },
    robots: { index: false, follow: false },
  };
}

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  return (
    <Document locale="fr">
      <AgentShell>{children}</AgentShell>
    </Document>
  );
}
