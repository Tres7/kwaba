import Decouvrir from "@/features/experiences/Decouvrir";

/** Discover page; ?ville= preselects a city (link "Things to do in Kpalimé" of the destination pages). */
export default async function DecouvrirPage({ searchParams }: { searchParams: Promise<{ ville?: string | string[] }> }) {
  const { ville } = await searchParams;
  return <Decouvrir villeInitiale={typeof ville === "string" ? ville : ""} />;
}
