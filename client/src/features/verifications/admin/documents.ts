import { toast } from "sonner";
import { apiErrorMessage, firstErrorMessage } from "@/lib/api";
import { lireFichierPiece } from "../api";

/** Opens the identity document: read with the agent's token (never a public URL), shown in a new tab. */
export async function ouvrirPiece(hoteId: string) {
  const onglet = window.open("", "_blank");
  try {
    const url = URL.createObjectURL(await lireFichierPiece(hoteId));
    if (onglet) onglet.location.href = url;
    else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    onglet?.close();
    // Asked for as a file: the API's message arrives as a Blob too
    const donnees = (err as { response?: { data?: unknown } }).response?.data;
    const message = donnees instanceof Blob ? firstErrorMessage(await donnees.text().then(JSON.parse).catch(() => null)) : undefined;
    toast.error(message ?? apiErrorMessage(err, "Document introuvable."));
  }
}
