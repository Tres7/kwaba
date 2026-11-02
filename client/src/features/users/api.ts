import api from "@/lib/api";
import type { AdminStats, AdminUser } from "@/types/api/admin";
import type { Me } from "@/types/api/models";

const MOI = "/v1/users/me/";

export async function lireMoi() {
  return (await api.get<Me>(MOI)).data;
}

export async function modifierMoi(champs: Partial<Pick<Me, "first_name" | "last_name" | "phone">>) {
  return (await api.patch<Me>(MOI, champs)).data;
}

export async function devenirHote() {
  await api.patch(MOI, { role: "hote" });
}

export async function fermerMonCompte() {
  await api.delete(MOI);
}

export async function modifierUtilisateurAdmin(id: AdminUser["id"], champs: Record<string, unknown>) {
  await api.patch(`/v1/admin/users/${id}/`, champs);
}

export async function lireStatsAdmin() {
  return (await api.get<AdminStats>("/v1/admin/stats/")).data;
}
