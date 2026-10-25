import { Children } from "react";

/** Liste de missions avec ses états : chargement, accès refusé, vide. */
export default function ListeMissions({ chargement, erreur, vide, children }: {
  chargement: boolean;
  erreur: boolean;
  vide: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mt-5 space-y-3">
      {chargement ? (
        [0, 1, 2].map((i) => <div key={i} className="h-24 skeleton rounded-2xl" />)
      ) : erreur ? (
        <p className="bg-red-50 text-red-700 rounded-2xl p-4 text-sm">Impossible de charger les missions (accès réservé aux agents de terrain).</p>
      ) : Children.count(children) === 0 ? (
        <p className="bg-white rounded-2xl p-8 text-center text-gray-500 border border-gray-100">{vide}</p>
      ) : (
        children
      )}
    </div>
  );
}
