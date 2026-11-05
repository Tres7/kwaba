import { describe, expect, it } from "vitest";
import type { Hebergement } from "@/types/api/models";
import { donneesLogement, filAriane, prixNuitAffiche } from "./donnees-structurees";
import { SITE_URL } from "./seo";

const logement = {
  id: "0b6f",
  name: "Villa Kéta",
  type: "villa",
  city: "Lome",
  location: "Bè Kpota",
  price_per_night: 30000,
  frais_voyageur: 0.06,
  image_url: "https://media.kwa-ba.com/a.jpg",
  images: ["https://media.kwa-ba.com/a.jpg", "/media/b.jpg"],
  chambres: 3,
  arrivee_a_partir: "14:00:00",
  depart_avant: null,
  rating: 4.5,
  review_count: 0,
  point_repere: "Derrière la pharmacie",
  position: { lat: 6.13, lng: 1.25, rayon_m: 300 },
} as unknown as Hebergement;

describe("données structurées", () => {
  it("shows the price of a night with the service fee, as the page", () => {
    expect(prixNuitAffiche(logement)).toBe(31800);
  });

  it("describes a listing without its exact place", () => {
    const d = donneesLogement(logement, "en", "A villa");
    expect(d["@type"]).toBe("LodgingBusiness");
    expect(d.url).toBe(`${SITE_URL}/en/hebergements/0b6f`);
    expect(d.address).toEqual({ "@type": "PostalAddress", addressLocality: "Lomé", addressCountry: "TG" });
    expect(d.image).toEqual(["https://media.kwa-ba.com/a.jpg", `${SITE_URL}/media/b.jpg`]);
    expect(d).toMatchObject({ numberOfRooms: 3, checkinTime: "14:00:00", makesOffer: { price: 31800, priceCurrency: "XOF" } });
    expect(d).not.toHaveProperty("aggregateRating");
    expect(d).not.toHaveProperty("checkoutTime");
    const texte = JSON.stringify(d);
    expect(texte).not.toContain("pharmacie");
    expect(texte).not.toContain("6.13");
  });

  it("uses the hotel type and the reviews when there are some", () => {
    const d = donneesLogement({ ...logement, type: "chambre_hotel", review_count: 4 }, "fr", "");
    expect(d["@type"]).toBe("Hotel");
    expect(d.aggregateRating).toMatchObject({ ratingValue: 4.5, reviewCount: 4 });
  });

  it("numbers the steps of the breadcrumb", () => {
    const fil = filAriane("fr", [{ nom: "Accueil", chemin: "/" }, { nom: "Togo", chemin: "/tg" }]);
    expect(fil.itemListElement).toEqual([
      { "@type": "ListItem", position: 1, name: "Accueil", item: `${SITE_URL}/` },
      { "@type": "ListItem", position: 2, name: "Togo", item: `${SITE_URL}/tg` },
    ]);
  });
});
