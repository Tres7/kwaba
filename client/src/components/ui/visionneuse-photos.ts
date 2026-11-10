/**
 * Keyboard focus of a photo that opens the viewer: drawn inside the photo, since an outline outside is cut
 * by the scrolling rows and the rounded mosaic around it.
 */
export const CONTOUR_FOCUS_PHOTO = "focus-visible:outline focus-visible:outline-[3px] focus-visible:-outline-offset-[3px] focus-visible:outline-primary";

/** Photos within one step of the one shown: the only ones the viewer adds to those it loads. */
export function voisines(index: number, total: number): number[] {
  return [index - 1, index, index + 1].filter((i) => i >= 0 && i < total);
}

/**
 * Photos whose file the viewer requests: those already loaded (going back must not show an empty frame)
 * and the neighbours of the one shown, so that the next one is ready before the swipe, without loading the whole gallery.
 */
export function photosAcharger(dejaChargees: Set<number>, index: number, total: number): Set<number> {
  const manquantes = voisines(index, total).filter((i) => !dejaChargees.has(i));
  // Same set when nothing is missing: React then skips the render
  return manquantes.length ? new Set([...dejaChargees, ...manquantes]) : dejaChargees;
}

/** The photo to show for a request: the viewer stops at the first and the last photo, it does not loop. */
export function bornerPhoto(index: number, total: number): number {
  return Math.max(0, Math.min(total - 1, index));
}
