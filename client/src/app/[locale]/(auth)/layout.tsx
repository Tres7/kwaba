import type { Metadata } from "next";

/** Sign-in, sign-up, code and forgotten password: never in Google (every /login?callbackUrl=… would be a duplicate
 *  page), but crawlable so that Google reads this "noindex" (see CHEMINS_PRIVES in lib/seo.ts). */
export const metadata: Metadata = {
  alternates: { canonical: null, languages: {} },
  robots: { index: false, follow: true },
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
