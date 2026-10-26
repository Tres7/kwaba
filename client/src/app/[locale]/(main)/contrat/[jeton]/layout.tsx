import type { Metadata } from "next";

/** Personal signature link: never indexed, never sent as a referrer. */
export const metadata: Metadata = {
  title: "Contrat",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
