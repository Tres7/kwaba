import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { langueDe } from "@/lib/seo";

/** Host wizard: full screen, without the site's menus, so that nothing distracts from the next question. Never indexed. */
export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const t = await getTranslations({ locale: langueDe((await params).locale), namespace: "assistantHote" });
  return {
    title: t("meta"),
    alternates: { canonical: null, languages: {} },
    robots: { index: false, follow: false },
  };
}

export default function AssistantLayout({ children }: { children: React.ReactNode }) {
  return children;
}
