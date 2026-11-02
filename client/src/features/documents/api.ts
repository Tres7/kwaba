import api from "@/lib/api";
import { telechargerPdf } from "@/lib/documents";
import type { FactureAdmin, SocieteAdmin } from "@/types/api/admin";

export type ObjetDocument = "reservation" | "transfert" | "location" | "don";
export type TypeDocument = "bon" | "recu" | "facture";

const FACTURES = "/v1/admin/documents/factures/";
const SOCIETE = "/v1/admin/documents/societe/";

export function telechargerDocument(objet: ObjetDocument, id: string, doc: TypeDocument) {
  return telechargerPdf(`/v1/documents/${objet}/${id}/${doc}/`, `${doc}-${id}.pdf`);
}

export function telechargerFacture(f: Pick<FactureAdmin, "id" | "numero">) {
  return telechargerPdf(`${FACTURES}${f.id}/pdf/`, `facture-${f.numero}.pdf`);
}

export async function emettreFacture(facture: Record<string, unknown>) {
  return (await api.post<FactureAdmin>(FACTURES, facture)).data;
}

/** Back-office: invoice of a paid stay, transfer or rental (issued only once), then downloaded. */
export async function factureDe(objet: Exclude<ObjetDocument, "don">, id: string): Promise<FactureAdmin> {
  const facture = await emettreFacture({ objet_type: objet, objet_id: id });
  await telechargerFacture(facture);
  return facture;
}

export async function lireSociete() {
  return (await api.get<SocieteAdmin>(SOCIETE)).data;
}

export async function enregistrerSociete(corps: FormData) {
  return (await api.put<SocieteAdmin>(SOCIETE, corps, { headers: { "Content-Type": "multipart/form-data" } })).data;
}

/** The saved signature is read through the API, never from a public address. */
export async function lireSignature() {
  return (await api.get<Blob>(`${SOCIETE}signature/`, { responseType: "blob" })).data;
}
