"use client";

import { useLocale } from "next-intl";
import { definirLangue } from "@/lib/utils";

/** Gives the current language to the format functions (dates, prices, labels). Rendered at the top of the tree, before the content. */
export default function SynchroLangue() {
  definirLangue(useLocale());
  return null;
}
