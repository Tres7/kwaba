import { ExperiencesAdmin } from "@/features/experiences";

export const metadata = { title: "Expériences" };

export default function ExperiencesPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Expériences</h1>
        <p className="text-muted text-sm mt-1">
          Activités, restaurants, loisirs et sites de la page Découvrir : ajout, photo, traduction anglaise, publication.
        </p>
      </div>
      <ExperiencesAdmin />
    </div>
  );
}
