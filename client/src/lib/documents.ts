import api, { apiErrorMessage, estErreurApi } from "@/lib/api";
import type { FactureAdmin } from "@/types/api/admin";

export type ObjetDocument = "reservation" | "transfert" | "location" | "don";
export type TypeDocument = "bon" | "recu" | "facture";

/** Name suggested by the server (Content-Disposition), otherwise a default name. */
function nomFichier(entete: string | undefined, defaut: string): string {
  const nom = entete?.match(/filename="?([^";]+)"?/)?.[1];
  return nom || defaut;
}

/** Downloads a PDF from the API (authenticated request) and saves it on the device. */
export async function telechargerPdf(url: string, defaut: string): Promise<void> {
  const res = await api.get<Blob>(url, { responseType: "blob" });
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(res.data);
  lien.download = nomFichier(res.headers["content-disposition"] as string | undefined, defaut);
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  setTimeout(() => URL.revokeObjectURL(lien.href), 10_000);
}

export function telechargerDocument(objet: ObjetDocument, id: string, doc: TypeDocument) {
  return telechargerPdf(`/v1/documents/${objet}/${id}/${doc}/`, `${doc}-${id}.pdf`);
}

/** Error message of a download: the response of a PDF is a Blob, the JSON has to be read again. */
export async function messageErreurPdf(err: unknown, defaut?: string): Promise<string> {
  if (estErreurApi(err) && err.response?.data instanceof Blob) {
    try {
      const corps = JSON.parse(await err.response.data.text()) as { detail?: string };
      if (corps.detail) return corps.detail;
    } catch { /* corps non JSON */ }
    if (defaut) return defaut;
  }
  return apiErrorMessage(err, defaut);
}

export function telechargerFacture(f: Pick<FactureAdmin, "id" | "numero">) {
  return telechargerPdf(`/v1/admin/documents/factures/${f.id}/pdf/`, `facture-${f.numero}.pdf`);
}

/** Back-office: invoice of a paid stay, transfer or rental (issued only once), then downloaded. */
export async function factureDe(objet: Exclude<ObjetDocument, "don">, id: string): Promise<FactureAdmin> {
  const { data } = await api.post<FactureAdmin>("/v1/admin/documents/factures/", { objet_type: objet, objet_id: id });
  await telechargerFacture(data);
  return data;
}
