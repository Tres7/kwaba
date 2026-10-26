"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, ImagePlus, Loader2, Star, Trash2, TriangleAlert } from "lucide-react";
import api, { apiErrorMessage } from "@/lib/api";
import { compressImage } from "@/lib/compressImage";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

export const MAX_PHOTOS = 10;
const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];

type Item =
  | { key: string; status: "done"; url: string; photoId?: string }
  | { key: string; status: "uploading"; preview: string; progress: number }
  | { key: string; status: "error"; preview: string; error: string };

interface PhotoUploaderProps {
  /** Photo URLs; the first one is the cover photo. */
  value: string[];
  onChange: (urls: string[]) => void;
  onBusyChange?: (busy: boolean) => void;
  error?: string;
}

let keySeq = 0;
const nextKey = () => `p${++keySeq}`;

export default function PhotoUploader({ value, onChange, onBusyChange, error }: PhotoUploaderProps) {
  const t = useTranslations("photos");
  const [items, setItems] = useState<Item[]>(() => value.map((url) => ({ key: nextKey(), status: "done", url })));
  const [dragOver, setDragOver] = useState(false);
  const [notice, setNotice] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const busy = items.some((i) => i.status === "uploading");
  const complet = items.length >= MAX_PHOTOS;
  const ouvrirChoix = () => {
    if (!complet) inputRef.current?.click();
  };

  // The form only knows the uploaded photos, in the displayed order
  useEffect(() => {
    onChange(items.flatMap((i) => (i.status === "done" ? [i.url] : [])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  useEffect(() => onBusyChange?.(busy), [busy, onBusyChange]);

  // Releases the local previews
  useEffect(() => () => items.forEach((i) => i.status !== "done" && URL.revokeObjectURL(i.preview)), []); // eslint-disable-line react-hooks/exhaustive-deps

  const update = (key: string, patch: Item) => setItems((prev) => prev.map((i) => (i.key === key ? patch : i)));

  const uploadOne = async (key: string, file: File, preview: string) => {
    try {
      const compressed = await compressImage(file);
      const body = new FormData();
      body.append("file", compressed);
      const res = await api.post<{ id: string; url: string }>("/v1/hebergements/photos/", body, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (e.total) update(key, { key, status: "uploading", preview, progress: Math.round((e.loaded / e.total) * 100) });
        },
      });
      URL.revokeObjectURL(preview);
      update(key, { key, status: "done", url: res.data.url, photoId: res.data.id });
    } catch (err) {
      update(key, { key, status: "error", preview, error: apiErrorMessage(err, t("envoiImpossible")) });
    }
  };

  const addFiles = async (fileList: FileList | File[]) => {
    setNotice("");
    const files = Array.from(fileList);
    const room = MAX_PHOTOS - items.length;
    const rejected = files.filter((f) => !ACCEPTED.includes(f.type));
    const accepted = files.filter((f) => ACCEPTED.includes(f.type)).slice(0, Math.max(0, room));

    if (rejected.length) setNotice(t("formats"));
    else if (files.length > accepted.length) setNotice(`${MAX_PHOTOS} photos maximum par annonce.`);
    if (!accepted.length) return;

    const queued = accepted.map((file) => ({ key: nextKey(), file, preview: URL.createObjectURL(file) }));
    setItems((prev) => [...prev, ...queued.map(({ key, preview }) => ({ key, status: "uploading" as const, preview, progress: 0 }))]);

    // Uploads one after the other: more reliable on a slow mobile connection
    for (const { key, file, preview } of queued) await uploadOne(key, file, preview);
  };

  const remove = (item: Item) => {
    if (item.status !== "done") URL.revokeObjectURL(item.preview);
    // Photo uploaded during this edit: the file is also deleted on the server
    if (item.status === "done" && item.photoId) api.delete(`/v1/hebergements/photos/${item.photoId}/`).catch(() => {});
    setItems((prev) => prev.filter((i) => i.key !== item.key));
  };

  const move = (index: number, delta: number) =>
    setItems((prev) => {
      const next = [...prev];
      const target = index + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });

  const makeCover = (index: number) =>
    setItems((prev) => [prev[index], ...prev.filter((_, i) => i !== index)]);

  return (
    <div>
      {/* The whole area opens the file picker (not only the word "browse"), with the mouse as with the keyboard */}
      <div
        role="button"
        tabIndex={complet ? -1 : 0}
        aria-disabled={complet}
        aria-label={t("ajouterPhotos")}
        onClick={ouvrirChoix}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ouvrirChoix(); } }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); }}
        className={cn(
          "rounded-2xl border-2 border-dashed p-6 text-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
          complet ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-primary/50 hover:bg-primary/5",
          dragOver ? "border-primary bg-primary/5" : error ? "border-red-300 bg-red-50/40" : "border-gray-200 bg-gray-50/60"
        )}
      >
        <ImagePlus size={28} className="mx-auto text-primary mb-2" />
        <p className="text-sm text-dark font-medium">
          <span className="hidden sm:inline">{t("glissez")} </span>
          <span className="text-primary font-bold underline-offset-2 hover:underline">
            <span className="sm:hidden">{t("ajouterPhotos")}</span><span className="hidden sm:inline">{t("parcourez")}</span>
          </span>
        </p>
        <p className="text-xs text-gray-500 mt-1">{t("limites", { nombre: items.length, max: MAX_PHOTOS })}</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          multiple
          className="hidden"
          // The programmatic click on this field must not bubble up to the area (which would open it again)
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ""; }}
        />
      </div>

      {(notice || error) && <p className="text-xs text-red-600 mt-2">{notice || error}</p>}

      {items.length > 0 && (
        <ul className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
          {items.map((item, index) => {
            const src = item.status === "done" ? item.url : item.preview;
            return (
              <li key={item.key} className={cn("relative aspect-[4/3] rounded-xl overflow-hidden bg-gray-100 group", index === 0 && item.status === "done" && "ring-2 ring-primary")}>
                <img src={src} alt={`Photo ${index + 1}`} className={cn("w-full h-full object-cover", item.status !== "done" && "opacity-60")} />

                {index === 0 && item.status === "done" && (
                  <span className="absolute top-2 left-2 bg-primary text-white text-[10px] font-bold uppercase px-2 py-1 rounded-full flex items-center gap-1">
                    <Star size={10} className="fill-white" /> {t("couverture")}
                  </span>
                )}

                {item.status === "uploading" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/30 text-white">
                    <Loader2 size={20} className="animate-spin" />
                    <div className="w-2/3 h-1.5 bg-white/40 rounded-full overflow-hidden">
                      <div className="h-full bg-white transition-all" style={{ width: `${item.progress}%` }} />
                    </div>
                  </div>
                )}

                {item.status === "error" && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-red-900/70 text-white p-2 text-center">
                    <TriangleAlert size={18} />
                    <p className="text-[11px] leading-tight">{item.error}</p>
                  </div>
                )}

                {item.status !== "uploading" && (
                  <div className="absolute bottom-0 inset-x-0 flex items-center justify-between gap-1 p-1.5 bg-gradient-to-t from-black/60 to-transparent">
                    <div className="flex gap-1">
                      {item.status === "done" && (
                        <>
                          <button type="button" onClick={() => move(index, -1)} disabled={index === 0} aria-label={t("gauche")} className="w-7 h-7 rounded-full bg-white/90 text-dark flex items-center justify-center disabled:opacity-40"><ArrowLeft size={14} /></button>
                          <button type="button" onClick={() => move(index, 1)} disabled={index === items.length - 1} aria-label={t("droite")} className="w-7 h-7 rounded-full bg-white/90 text-dark flex items-center justify-center disabled:opacity-40"><ArrowRight size={14} /></button>
                          {index !== 0 && (
                            <button type="button" onClick={() => makeCover(index)} aria-label={t("definirCouverture")} title={t("definirCouverture")} className="w-7 h-7 rounded-full bg-white/90 text-primary flex items-center justify-center"><Star size={14} /></button>
                          )}
                        </>
                      )}
                    </div>
                    <button type="button" onClick={() => remove(item)} aria-label={t("retirer")} className="w-7 h-7 rounded-full bg-white/90 text-red-600 flex items-center justify-center"><Trash2 size={14} /></button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
