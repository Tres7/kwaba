import Tarifs from "@/features/paiements/admin/Tarifs";

export default function TarifsPage() {
  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Tarifs</h1>
        <p className="text-muted text-sm mt-1">Frais de service, commissions et frais de ménage, modifiables sans nouveau déploiement.</p>
      </div>
      <Tarifs />
    </div>
  );
}
