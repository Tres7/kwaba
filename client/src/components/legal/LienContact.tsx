import { CONTACT_EMAIL } from "@/lib/contact";

/** "mailto" link to the contact address, with an optional prefilled subject. */
export default function LienContact({ sujet }: { sujet?: string }) {
  const href = `mailto:${CONTACT_EMAIL}${sujet ? `?subject=${encodeURIComponent(sujet)}` : ""}`;
  return <a href={href}>{CONTACT_EMAIL}</a>;
}
