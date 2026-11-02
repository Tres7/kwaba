import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import { creerExperience, listerExperiences, listerExperiencesAdmin, modifierExperience, supprimerExperience } from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } }));

const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };

describe("experiences", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lit le guide public et la liste du back-office", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: 1 }] });
    await expect(listerExperiences()).resolves.toEqual([{ id: 1 }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/experiences/");
    await expect(listerExperiencesAdmin()).resolves.toEqual([{ id: 1 }]);
    expect(api.get).toHaveBeenLastCalledWith("/v1/admin/experiences/");
  });

  it("envoie la photo en multipart à la création et à la modification", async () => {
    const corps = new FormData();
    await creerExperience(corps);
    expect(api.post).toHaveBeenCalledWith("/v1/admin/experiences/", corps, MULTIPART);
    await modifierExperience(3, corps);
    expect(api.patch).toHaveBeenCalledWith("/v1/admin/experiences/3/", corps, MULTIPART);
  });

  it("supprime une expérience", async () => {
    await supprimerExperience(3);
    expect(api.delete).toHaveBeenCalledWith("/v1/admin/experiences/3/");
  });
});
