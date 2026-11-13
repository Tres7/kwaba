import GrandLivre from "@/features/finance/admin/GrandLivre";

export default function GrandLivrePage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Grand livre</h1>
        <p className="text-muted text-sm mt-1">Chaque mouvement d&apos;argent écrit une seule fois : contrôle des invariants, les trois soldes qui ne se mélangent jamais, sommes dues et dernières lignes.</p>
      </div>
      <GrandLivre />
    </div>
  );
}
