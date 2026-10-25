import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";

/** Ouvre la pièce d'identité : lue avec le jeton de l'agent (jamais d'URL publique), affichée dans un nouvel onglet. */
export async function ouvrirPiece(hoteId: string) {
  const onglet = window.open("", "_blank");
  try {
    const res = await api.get<Blob>(`/v1/verifications/identite/${hoteId}/fichier/`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    if (onglet) onglet.location.href = url;
    else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    onglet?.close();
    toast.error(apiErrorMessage(err, "Document introuvable."));
  }
}
