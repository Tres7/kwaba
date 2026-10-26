const MAX_DIMENSION = 2000;
const QUALITY = 0.85;
// Below this, the image is sent as is (the server normalises it anyway)
const SKIP_BELOW_BYTES = 800 * 1024;

/**
 * Shrinks a photo in the browser before upload (less data on slow mobile connections).
 * Returns the original file if the browser cannot decode it (e.g. HEIC) or if shrinking brings nothing.
 */
export async function compressImage(file: File): Promise<File> {
  if (file.size <= SKIP_BELOW_BYTES || typeof createImageBitmap === "undefined") return file;

  let bitmap: ImageBitmap;
  try {
    // imageOrientation: applies the phone's EXIF rotation
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    return file;
  }

  const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    return file;
  }
  // White background: transparent areas of a PNG do not turn black in JPEG
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", QUALITY));
  if (!blob || blob.size >= file.size) return file;

  const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
  return new File([blob], name, { type: "image/jpeg", lastModified: Date.now() });
}
