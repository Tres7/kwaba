import { metadataTraduite } from "@/lib/seo";

export function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
  return metadataTraduite(params, "payer", "/payer");
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
