import { describe, expect, it } from "vitest";
import type { LayerSpecification, StyleSpecification } from "maplibre-gl";
import { auxCouleursKwaBa } from "./style";

const style = (layers: unknown[]) => ({ version: 8, sources: {}, layers }) as unknown as StyleSpecification;
const couche = (resultat: StyleSpecification, id: string) => resultat.layers.find((l) => l.id === id) as LayerSpecification & { paint: Record<string, unknown> };

describe("auxCouleursKwaBa", () => {
  it("colours the known layers and keeps their other settings", () => {
    const resultat = auxCouleursKwaBa(style([{ id: "water", type: "fill", source: "t", paint: { "fill-opacity": 0.5, "fill-color": "red" } }]));

    expect(couche(resultat, "water").paint).toEqual({ "fill-opacity": 0.5, "fill-color": "#BEDCD8" });
  });

  it("gives every label a readable colour, except road shields", () => {
    const resultat = auxCouleursKwaBa(style([
      { id: "label_city", type: "symbol", source: "t" },
      { id: "water_name_point_label", type: "symbol", source: "t" },
      { id: "highway-shield-non-us", type: "symbol", source: "t" },
    ]));

    expect(couche(resultat, "label_city").paint["text-color"]).toBe("#1F2937");
    expect(couche(resultat, "water_name_point_label").paint["text-color"]).toBe("#0E4D47");
    expect(couche(resultat, "highway-shield-non-us").paint).toBeUndefined();
  });

  it("leaves an unknown layer as it is", () => {
    const inconnue = { id: "nouvelle_couche", type: "line", source: "t", paint: { "line-color": "red" } };

    expect(couche(auxCouleursKwaBa(style([inconnue])), "nouvelle_couche")).toEqual(inconnue);
  });
});
