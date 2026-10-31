"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LngLatBounds, Marker, type Map as CarteGl } from "maplibre-gl";
import { MapPin, X } from "lucide-react";
import { useTranslations } from "next-intl";
import RatingBadge from "@/components/ui/RatingBadge";
import { Link } from "@/i18n/navigation";
import { useFormat } from "@/lib/format";
import { FALLBACK_IMAGE, SERVICE_FEE_RATE, cn, prixNuitFraisInclus } from "@/lib/utils";
import type { Hebergement } from "@/types/api/models";
import { CENTRE_LOME, centreDeVille, regrouper } from "./geometrie";
import { CadreCarte, useCarte } from "./useCarte";

const PASTILLE = "block rounded-full px-2.5 py-1 text-[13px] font-bold whitespace-nowrap shadow-md transition-transform duration-150";
// Size of a price on the map: two closer than this would overlap, they are gathered
const TAILLE_PASTILLE = { largeur: 84, hauteur: 34 };
const ZOOM_MAX_CADRAGE = 14;
const ZOOM_SANS_GROUPES = 15;
// More room at the bottom: the preview and the Concierge button sit there
const MARGES = { top: 72, right: 72, bottom: 110, left: 72 };

/** Price of a night as on the cards: service fee included. */
const prixNuit = (h: Hebergement) => prixNuitFraisInclus(Number(h.price_per_night), h.frais_voyageur ?? SERVICE_FEE_RATE).total;

interface Point {
  id: string;
  lat: number;
  lng: number;
  complet: boolean;
  prix: string;
  libelle: string;
}

interface Pastille {
  element: HTMLElement;
  ids: string[];
  complet: boolean;
  groupe: boolean;
}

function dessinerPastille({ element, complet, groupe }: Pastille, actif: boolean) {
  const repos = complet ? "bg-gray-100 text-gray-500" : groupe ? "bg-dark text-white hover:scale-105" : "bg-white text-dark hover:scale-105";
  element.className = cn(PASTILLE, actif ? "bg-primary text-white scale-110" : repos);
  if (element.parentElement) element.parentElement.style.zIndex = actif ? "2" : "";
}

const limitesDe = (points: Pick<Point, "lat" | "lng">[]) => points.reduce(
  (limites, p) => limites.extend([p.lng, p.lat]),
  new LngLatBounds([points[0].lng, points[0].lat], [points[0].lng, points[0].lat]),
);

/** Search results on a map, a price on each listing. `survol`: the listing pointed at in the list. */
export default function CarteResultats({ logements, query, ville, survol }: {
  logements: Hebergement[];
  query: string;
  ville: string;
  survol: string | null;
}) {
  const t = useTranslations("carte");
  const tl = useTranslations("logement");
  const { formatPrice, formatPrixCourt } = useFormat();
  const depart = centreDeVille(ville) ?? CENTRE_LOME;
  const { conteneur, carte, panne } = useCarte({ center: [depart.lng, depart.lat], zoom: 11 });
  const pastilles = useRef<Pastille[]>([]);
  const enAvant = useRef(new Set<string>());
  const [choisi, setChoisi] = useState<string | null>(null);

  const points = useMemo<Point[]>(() => logements.flatMap((h) => (h.position ? [{
    id: h.id, lat: h.position.lat, lng: h.position.lng, complet: h.disponibilite?.disponible === false,
    prix: formatPrixCourt(prixNuit(h)), libelle: t("voirLogement", { nom: h.name, prix: formatPrice(prixNuit(h)) }),
  }] : [])), [logements, formatPrice, formatPrixCourt, t]);

  const mettreEnAvant = useCallback(() => {
    pastilles.current.forEach((p) => dessinerPastille(p, p.ids.some((id) => enAvant.current.has(id))));
  }, []);

  const creerMarqueur = useCallback((instance: CarteGl, membres: Point[]) => {
    const seul = membres.length === 1 ? membres[0] : null;
    const bouton = document.createElement("button");
    const element = document.createElement("span");
    bouton.type = "button";
    bouton.setAttribute("aria-label", seul ? seul.libelle : t("zoomerGroupe", { nombre: membres.length }));
    element.textContent = seul ? seul.prix : t("groupe", { nombre: membres.length });
    bouton.append(element);
    bouton.addEventListener("click", (e) => {
      // Stops here: the map would take this click for a click beside the prices
      e.stopPropagation();
      if (seul) setChoisi(seul.id);
      else instance.fitBounds(limitesDe(membres), { padding: MARGES, maxZoom: ZOOM_SANS_GROUPES, duration: 400 });
    });
    pastilles.current.push({ element, ids: membres.map((m) => m.id), complet: membres.every((m) => m.complet), groupe: !seul });
    const centre = limitesDe(membres).getCenter();
    return new Marker({ element: bouton }).setLngLat(seul ? [seul.lng, seul.lat] : centre).addTo(instance);
  }, [t]);

  useEffect(() => {
    if (!carte) return;
    let marqueurs: Marker[] = [];
    const retirer = () => {
      marqueurs.forEach((m) => m.remove());
      pastilles.current = [];
    };
    const dessiner = () => {
      retirer();
      const groupes = carte.getZoom() >= ZOOM_SANS_GROUPES
        ? points.map((p) => [p])
        : regrouper(points.map((p) => ({ ...p, ...carte.project([p.lng, p.lat]) })), TAILLE_PASTILLE);
      marqueurs = groupes.map((membres) => creerMarqueur(carte, membres));
      mettreEnAvant();
    };
    dessiner();
    carte.on("zoomend", dessiner);
    return () => {
      carte.off("zoomend", dessiner);
      retirer();
    };
  }, [carte, points, creerMarqueur, mettreEnAvant]);

  useEffect(() => {
    enAvant.current = new Set([choisi, survol].filter((id): id is string => !!id));
    mettreEnAvant();
  }, [choisi, survol, mettreEnAvant]);

  // Compared as text: a new order of the same listings must not move the map the visitor is reading
  const positions = JSON.stringify(points.map(({ lat, lng }) => ({ lat, lng })).sort((a, b) => a.lat - b.lat || a.lng - b.lng));
  useEffect(() => {
    if (!carte) return;
    const liste = JSON.parse(positions) as Pick<Point, "lat" | "lng">[];
    if (liste.length) carte.fitBounds(limitesDe(liste), { padding: MARGES, maxZoom: ZOOM_MAX_CADRAGE, duration: 400 });
  }, [carte, positions]);

  useEffect(() => {
    if (!carte) return;
    const fermer = () => setChoisi(null);
    carte.on("click", fermer);
    return () => { carte.off("click", fermer); };
  }, [carte]);

  const apercu = logements.find((h) => h.id === choisi);
  const sansPosition = logements.length - points.length;

  return (
    <CadreCarte conteneur={conteneur} charge={!!carte} panne={panne}>
      {carte && !panne && (points.length === 0 || sansPosition > 0) && (
        <p className="absolute top-16 lg:top-3 left-3 right-14 sm:right-auto sm:max-w-xs rounded-xl bg-white/95 px-3 py-2 text-xs font-semibold text-dark shadow-md">
          {points.length === 0 ? t("aucunLogement") : t("sansPosition", { nombre: sansPosition })}
        </p>
      )}
      {apercu && (
        <div className="absolute inset-x-3 bottom-9 sm:inset-x-auto sm:left-3 sm:w-80 rounded-2xl bg-white shadow-card-hover">
          <Link href={`/hebergements/${apercu.id}${query}`} className="flex overflow-hidden rounded-2xl">
            <img src={apercu.image_url || FALLBACK_IMAGE} alt="" className="w-28 flex-shrink-0 object-cover" />
            <div className="min-w-0 flex-1 p-3 pr-8">
              <p className="font-heading text-sm font-semibold text-dark truncate">{apercu.name}</p>
              <p className="mt-0.5 flex items-center gap-1 text-xs text-gray-500">
                <MapPin size={11} className="flex-shrink-0" aria-hidden />
                <span className="truncate">{apercu.location ? `${apercu.location}, ` : ""}{apercu.city}</span>
              </p>
              <RatingBadge rating={apercu.rating} count={apercu.review_count} className="mt-1" />
              <p className="mt-1 text-sm">
                <span className="font-heading font-bold text-primary">{formatPrice(prixNuit(apercu))}</span>
                <span className="text-xs text-gray-500"> {tl("parNuitFraisInclus")}</span>
              </p>
            </div>
          </Link>
          <button type="button" onClick={() => setChoisi(null)} aria-label={t("fermer")}
            className="absolute top-1.5 right-1.5 rounded-full bg-white/90 p-1 text-dark hover:bg-gray-100">
            <X size={15} aria-hidden />
          </button>
        </div>
      )}
    </CadreCarte>
  );
}
