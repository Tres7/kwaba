import type { LayerSpecification, StyleSpecification } from "maplibre-gl";

/** Free vector tiles, without a key or a cookie (openfreemap.org). Its host is also in the CSP (lib/csp.ts). */
export const STYLE_CARTE = "https://tiles.openfreemap.org/styles/positron";

// Site colours (tailwind.config.ts) on this neutral base style. A layer it renames simply keeps its own colour.
const CREME = "#F8F6F2";
const EAU = "#BEDCD8";
const VEGETATION = "#DCEAD6";
const VERT = "#0E4D47";
const ENCRE = "#1F2937";
const GRIS = "#6B7280";
const BORDURE = "#E4DCCD";
const BLANC = "#FFFFFF";

const COULEURS: Record<string, Record<string, string>> = {
  background: { "background-color": CREME },
  water: { "fill-color": EAU },
  waterway: { "line-color": EAU },
  park: { "fill-color": VEGETATION },
  landcover_wood: { "fill-color": VEGETATION },
  landuse_residential: { "fill-color": "#F3EFE7" },
  building: { "fill-color": "#ECE5D8", "fill-outline-color": BORDURE },
  highway_path: { "line-color": BORDURE },
  highway_minor: { "line-color": BLANC },
  highway_major_inner: { "line-color": BLANC },
  highway_major_casing: { "line-color": BORDURE },
  highway_major_subtle: { "line-color": BORDURE },
  highway_motorway_inner: { "line-color": BLANC },
  highway_motorway_casing: { "line-color": BORDURE },
  highway_motorway_subtle: { "line-color": BORDURE },
  highway_motorway_bridge_inner: { "line-color": BLANC },
  highway_motorway_bridge_casing: { "line-color": BORDURE },
};

function couleursDe(couche: LayerSpecification): Record<string, string> | undefined {
  if (COULEURS[couche.id]) return COULEURS[couche.id];
  if (couche.type !== "symbol" || couche.id.includes("shield")) return undefined;
  const texte = couche.id.startsWith("water") ? VERT : couche.id.startsWith("label") ? ENCRE : GRIS;
  return { "text-color": texte, "text-halo-color": CREME };
}

/** The base style in Kwa-Ba colours, applied before the first drawing. */
export function auxCouleursKwaBa(style: StyleSpecification): StyleSpecification {
  return {
    ...style,
    layers: style.layers.map((couche) => {
      const couleurs = couleursDe(couche);
      return couleurs ? ({ ...couche, paint: { ...couche.paint, ...couleurs } } as LayerSpecification) : couche;
    }),
  };
}
