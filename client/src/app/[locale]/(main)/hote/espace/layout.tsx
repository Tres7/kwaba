import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { langueDe } from "@/lib/seo";

/** Private space: its own title, neither indexed nor attached to the public "Become a host" page (/hote). */
export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const t = await getTranslations({ locale: langueDe((await params).locale), namespace: "nav" });
  return {
    title: t("espaceHote"),
    alternates: { canonical: null, languages: {} },
    robots: { index: false, follow: false },
  };
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
