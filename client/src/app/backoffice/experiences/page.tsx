import ExperiencesAdmin from "@/features/experiences/admin/Experiences";

export const metadata = { title: "Expériences" };

export default function ExperiencesPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-dark">Expériences</h1>
        <p className="text-muted text-sm mt-1">
          Sites, activités et loisirs de la page Découvrir : ajout, photo, traduction anglaise, publication. Seules les fiches du Togo sont
          affichées, et les restaurants restent masqués sur le site pour le moment.
        </p>
      </div>
      <ExperiencesAdmin />
    </div>
  );
}
