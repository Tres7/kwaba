import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";

/** Opens the identity document: read with the agent's token (never a public URL), shown in a new tab. */
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
