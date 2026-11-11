"use client";

import { useConfigPublique } from "@/providers/PublicConfigProvider";

/** "mailto" link to the contact address of the environment, with an optional prefilled subject. */
export default function LienContact({ sujet }: { sujet?: string }) {
  const { contactEmail } = useConfigPublique();
  const href = `mailto:${contactEmail}${sujet ? `?subject=${encodeURIComponent(sujet)}` : ""}`;
  return <a href={href}>{contactEmail}</a>;
}
