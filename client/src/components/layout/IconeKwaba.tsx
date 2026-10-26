import { useId } from "react";

/** Kwa-Ba pictogram: the orange "A" (rising sun and waves) on a rounded green square. */
export default function IconeKwaba({ taille = 64, className }: { taille?: number; className?: string }) {
  const id = useId();
  return (
    <svg width={taille} height={taille} viewBox="0 0 64 64" className={className} role="img" aria-label="Kwa-Ba">
      <defs>
        <linearGradient id={`${id}-a`} x1="20" y1="10" x2="46" y2="52" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FBBF24" />
          <stop offset="0.5" stopColor="#F59E0B" />
          <stop offset="1" stopColor="#C2410C" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="15" fill="#0E4D47" />
      <path d="M12 51 L28.6 15.5 Q32 9 35.4 15.5 L52 51 L43.5 51 L32 26.5 L20.5 51 Z" fill={`url(#${id}-a)`} />
      <circle cx="32" cy="40.5" r="5.2" fill="#FBBF24" />
      <path d="M16 50.5 Q32 37.5 48 50.5" stroke="#F8F6F2" strokeWidth="3" strokeLinecap="round" fill="none" />
      <path d="M22 54 Q32 46.5 42 54" stroke="#F59E0B" strokeWidth="2.4" strokeLinecap="round" fill="none" />
    </svg>
  );
}
