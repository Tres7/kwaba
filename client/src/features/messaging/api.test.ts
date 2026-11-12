import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "@/lib/api";
import {
  checkDraft, compterNonLus, confirmReport, contacterHote, contacterVoyageur, contestSanction, envoyerMessage, getModerationStatus, getReport,
  liftSanction, lireConversation, listerConversations, listerMessages, marquerLu, rejectReport, reportFalsePositive, reportMessage, reviewContest,
  setReportLegalHold, traiterAlerteFraude,
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

  it("garde l'id de conversation de l'adresse dans un seul segment", async () => {
    await marquerLu("../../hebergements/brouillons?", 1);
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/..%2F..%2Fhebergements%2Fbrouillons%3F/read/", { up_to_id: 1 });
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

  it("sends the explicit confirmation only when the sender confirmed", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: 8 } });
    await envoyerMessage("c1", "Bonjour", true);
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/c1/messages/", { content: "Bonjour", confirmed: true });
  });

  it("checks a draft while typing", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { level: "block", categories: ["insult"] } });
    await expect(checkDraft("texte")).resolves.toEqual({ level: "block", categories: ["insult"] });
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/moderation/check/", { content: "texte" });
  });

  it("reports a wrongly blocked draft", async () => {
    await reportFalsePositive("c1", "texte");
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/c1/false-positive/", { content: "texte" });
  });

  it("reports a received message with a reason", async () => {
    await reportMessage("c1", 12, "threat", "Il me menace");
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/conversations/c1/messages/12/report/", { reason: "threat", details: "Il me menace" });
  });

  it("reads the moderation status and contests a sanction", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { suspended_until: null, sanctions: [] } });
    await expect(getModerationStatus()).resolves.toEqual({ suspended_until: null, sanctions: [] });
    expect(api.get).toHaveBeenCalledWith("/v1/messaging/moderation/status/");
    vi.mocked(api.post).mockResolvedValue({ data: { id: 3 } });
    await contestSanction(3, "Je conteste");
    expect(api.post).toHaveBeenCalledWith("/v1/messaging/moderation/sanctions/3/contest/", { text: "Je conteste" });
  });

  it("drives reports and sanctions from the back-office", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { id: 5 } });
    vi.mocked(api.post).mockResolvedValue({ data: { id: 9 } });
    await getReport(5);
    expect(api.get).toHaveBeenCalledWith("/v1/admin/anti-fraude/reports/5/");
    await confirmReport(5, "Confirmé");
    expect(api.post).toHaveBeenCalledWith("/v1/admin/anti-fraude/reports/5/confirm/", { note: "Confirmé" });
    await rejectReport(5, "");
    expect(api.post).toHaveBeenCalledWith("/v1/admin/anti-fraude/reports/5/reject/", { note: "" });
    await setReportLegalHold(5, true);
    expect(api.post).toHaveBeenCalledWith("/v1/admin/anti-fraude/reports/5/legal-hold/", { hold: true });
    await reviewContest(9, false, "Maintenue");
    expect(api.post).toHaveBeenCalledWith("/v1/admin/anti-fraude/sanctions/9/contest/", { accept: false, note: "Maintenue" });
    await liftSanction(9);
    expect(api.post).toHaveBeenCalledWith("/v1/admin/anti-fraude/sanctions/9/lift/", {});
  });
});
