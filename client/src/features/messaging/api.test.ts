import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import {
  compterNonLus, contacterHote, contacterVoyageur, envoyerMessage, lireConversation, listerConversations, listerMessages, marquerLu, traiterAlerteFraude,
} from "./api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));

describe("messaging", () => {
  beforeEach(() => vi.clearAllMocks());

  it("liste les conversations", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { results: [{ id: "c1" }] } });
    await expect(listerConversations()).resolves.toEqual([{ id: "c1" }]);
    expect(api.get).toHaveBeenCalledWith("/v1/messaging/conversations/");
  });

  it("lit une conversation", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { id: "c1" } });
    await expect(lireConversation("c1")).resolves.toEqual({ id: "c1" });
    expect(api.get).toHaveBeenCalledWith("/v1/messaging/conversations/c1/");
  });

  it("ne lit que les nouveaux messages après le dernier connu", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { results: [] } });
    await listerMessages("c1", 42);
    expect(api.get).toHaveBeenCalledWith("/v1/messaging/conversations/c1/messages/", { params: { after: 42 } });
  });

  it("envoie un message et renvoie sa version enregistrée", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: 7, masked: true } });
    await expect(envoyerMessage("c1", "Bonjour")).resolves.toEqual({ id: 7, masked: true });
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/c1/messages/", { content: "Bonjour" });
  });

  it("marque comme lu jusqu'au dernier message affiché", async () => {
    await marquerLu("c1", 42);
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/c1/read/", { up_to_id: 42 });
  });

  it("compte les messages non lus", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { unread_count: 3 } });
    await expect(compterNonLus()).resolves.toBe(3);
    expect(api.get).toHaveBeenCalledWith("/v1/messaging/unread-count/");
  });

  it("traite une alerte de fraude depuis le back-office", async () => {
    await traiterAlerteFraude(7, "Compte averti");
    expect(api.post).toHaveBeenCalledWith("/v1/admin/anti-fraude/7/traiter/", { note: "Compte averti" });
  });

  it("contacte un hôte depuis une annonce", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "c1" } });
    await contacterHote("h1");
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/", { hebergement_id: "h1" });
  });

  it("contacte un voyageur depuis une réservation", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "c1" } });
    await contacterVoyageur("r1");
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/avec-voyageur/", { reservation_id: "r1" });
  });
});
