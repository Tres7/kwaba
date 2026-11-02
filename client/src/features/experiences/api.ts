import api from "@/lib/api";
import type { ExperienceAdmin } from "@/types/api/admin";
import type { Experience } from "./types";

const ADMIN = "/v1/admin/experiences/";
// The API client sends JSON by default: header needed to send the photo
const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

export async function listerExperiences() {
  return (await api.get<Experience[]>("/v1/experiences/")).data;
}

export async function listerExperiencesAdmin() {
  return (await api.get<ExperienceAdmin[]>(ADMIN)).data;
}

export async function creerExperience(corps: FormData) {
  await api.post(ADMIN, corps, MULTIPART);
}

export async function modifierExperience(id: ExperienceAdmin["id"], corps: FormData) {
  await api.patch(`${ADMIN}${id}/`, corps, MULTIPART);
}

export async function supprimerExperience(id: ExperienceAdmin["id"]) {
  await api.delete(`${ADMIN}${id}/`);
}
