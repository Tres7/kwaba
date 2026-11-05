/**
 * Structured data (lib/donnees-structurees.ts) in the page. "<" is escaped: a listing name written by a host cannot
 * close the script. A JSON block is never executed, so the CSP does not ask for its nonce.
 */
export default function JsonLd({ donnees }: { donnees: object | object[] }) {
  const json = JSON.stringify(donnees).replace(/</g, "\\u003c");
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
