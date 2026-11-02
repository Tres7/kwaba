import { useQuery } from "@tanstack/react-query";
import { lireCatalogue, listerCategories, listerLieux, listerLoueurs } from "./api";

export const clesLocations = {
  mesLocations: ["locations"],
  location: (id: string) => ["location", id],
  admin: ["admin", "location"],
};

export function useCatalogue() {
  return useQuery({ queryKey: ["location", "catalogue"], queryFn: lireCatalogue });
}

export function useCategoriesAdmin() {
  return useQuery({ queryKey: [...clesLocations.admin, "categories"], queryFn: listerCategories });
}

export function useLoueursAdmin() {
  return useQuery({ queryKey: [...clesLocations.admin, "loueurs"], queryFn: listerLoueurs });
}

export function useLieuxAdmin() {
  return useQuery({ queryKey: [...clesLocations.admin, "lieux"], queryFn: listerLieux });
}
