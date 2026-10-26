/**
 * The <html> and <body> tags are rendered by app/[locale]/layout.tsx (site, FR or EN)
 * and by app/backoffice/layout.tsx: this way a language change rebuilds the whole page.
 */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
