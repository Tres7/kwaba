import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { langueDe, metadataPage } from "@/lib/seo";
import ContenuEn from "./en";
import ContenuFr from "./fr";
import { tauxCgv } from "./taux";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const locale = langueDe((await params).locale);
  const t = await getTranslations({ locale, namespace: "legal.titres" });
  return metadataPage({ locale, chemin: "/cgv", titre: t("cgv") });
}

/** Legal page: French or English version depending on the language (the French version is authoritative). The fee
 * rates are the ones set in the back-office. */
export default async function Page() {
  const locale = langueDe(await getLocale());
  const taux = await tauxCgv(locale);
  return locale === "en" ? <ContenuEn taux={taux} /> : <ContenuFr taux={taux} />;
}
