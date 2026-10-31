import api, { apiErrorMessage, estErreurApi } from "@/lib/api";

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

