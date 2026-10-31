"use client";

import { useRevenus } from "@/features/paiements";
import { creerHebergement, modifierHebergement } from "./api";
import { useCallback, useState } from "react";
import { firstErrorMessage } from "@/lib/api";
import { useEquipements } from "./AmenityBadge";
import PhotoUploader from "./PhotoUploader";
import EstimateurRevenus from "./EstimateurRevenus";
import { ChoixPosition, type PointCarte } from "@/features/carte";
import Select from "@/components/ui/Select";
import Stepper from "@/components/ui/Stepper";
import { cn } from "@/lib/utils";
import type { Hebergement, HebergementType, PolitiqueAnnulation } from "@/types/api/models";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useFormat } from "@/lib/format";

// Aide de chaque type de logement : messages annonce.types.<type>
// Cancellation policies chosen by the host (terms of sale, appendix 1): messages politiqueAnnulation.<politique>
const POLITIQUES: PolitiqueAnnulation[] = ["souple", "moderee", "ferme"];

interface HebergementFormProps {
  initial?: Hebergement;
  onSaved: (h: Hebergement) => void;
  onCancel: () => void;
}

const inputClass = "w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-base sm:text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary";
const labelClass = "block text-xs font-bold text-dark uppercase tracking-wide mb-2";

export default function HebergementForm({ initial, onSaved, onCancel }: HebergementFormProps) {
  const { CATEGORIES_EQUIPEMENTS, REGLES } = useEquipements();
  const { TYPE_LABELS } = useFormat();
  const t = useTranslations("annonce");
  const tp = useTranslations("politiqueAnnulation");
  // Partner type set by the team (individual, hotel, founder): the preview's commission is theirs
  const { data: revenus } = useRevenus();
  const [form, setForm] = useState({
    name: initial?.name ?? "",
    type: initial?.type ?? "appartement",
    city: initial?.city ?? "",
    location: initial?.location ?? "",
    price_per_night: initial ? String(initial.price_per_night) : "",
    max_guests: initial ? String(initial.max_guests) : "2",
    description: initial?.description ?? "",
    amenities: initial?.amenities ?? [],
    surface_m2: initial?.surface_m2 ? String(initial.surface_m2) : "",
    chambres: initial?.chambres ?? 1,
    salles_de_bain: initial?.salles_de_bain ?? 1,
    lits_doubles: initial?.lits_doubles ?? (initial ? 0 : 1),
    lits_simples: initial?.lits_simples ?? 0,
    canapes_lits: initial?.canapes_lits ?? 0,
    petit_dejeuner: initial?.petit_dejeuner || "",
    petit_dejeuner_prix: initial?.petit_dejeuner_prix ? String(initial.petit_dejeuner_prix) : "",
    arrivee_a_partir: initial?.arrivee_a_partir?.slice(0, 5) ?? "14:00",
    depart_avant: initial?.depart_avant?.slice(0, 5) ?? "11:00",
    politique_annulation: initial?.politique_annulation ?? "moderee",
  });
  // Photos in display order: the first one is the cover
  const [photos, setPhotos] = useState<string[]>(() => {
    const all = [initial?.image_url, ...(initial?.images ?? [])].filter((u): u is string => !!u);
    return Array.from(new Set(all));
  });
  // Exact position: required for a new listing, optional for one created before the map
  const [position, setPosition] = useState<PointCarte | null>(() => (
    initial?.latitude && initial.longitude ? { lat: Number(initial.latitude), lng: Number(initial.longitude) } : null
  ));
  const [uploading, setUploading] = useState(false);
  // Copyright and image rights: the host certifies they own the rights to the published photos
  const [droitsPhotos, setDroitsPhotos] = useState(!!initial);
  const onPhotosChange = useCallback((urls: string[]) => setPhotos(urls), []);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const toggleAmenity = (a: string) =>
    setForm((prev) => ({ ...prev, amenities: prev.amenities.includes(a) ? prev.amenities.filter((x) => x !== a) : [...prev.amenities, a] }));
  // House rule: one value of the pair, or none ("not specified")
  const choisirRegle = (regle: (typeof REGLES)[number], valeur: string | null) =>
    setForm((prev) => ({
      ...prev,
      amenities: [...prev.amenities.filter((x) => x !== regle.oui.id && x !== regle.non.id), ...(valeur ? [valeur] : [])],
    }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!droitsPhotos) {
      setErrors({ droits: t("erreurDroits") });
      return;
    }
    if (photos.length === 0) {
      setErrors({ photos: t("erreurPhotos") });
      return;
    }
    if (!position && !initial) {
      setErrors({ latitude: t("erreurPosition") });
      return;
    }
    setSaving(true);
    setErrors({});
    const payload = {
      name: form.name.trim(),
      type: form.type,
      city: form.city.trim(),
      location: form.location.trim(),
      ...(position ? { latitude: position.lat, longitude: position.lng } : {}),
      price_per_night: Number(form.price_per_night),
      max_guests: Number(form.max_guests),
      description: form.description.trim(),
      image_url: photos[0],
      images: photos,
      amenities: form.amenities,
      surface_m2: form.surface_m2 ? Number(form.surface_m2) : null,
      chambres: form.chambres,
      salles_de_bain: form.salles_de_bain,
      lits_doubles: form.lits_doubles,
      lits_simples: form.lits_simples,
      canapes_lits: form.canapes_lits,
      petit_dejeuner: form.petit_dejeuner,
      petit_dejeuner_prix: form.petit_dejeuner === "option" && form.petit_dejeuner_prix ? Number(form.petit_dejeuner_prix) : null,
      arrivee_a_partir: form.arrivee_a_partir || null,
      depart_avant: form.depart_avant || null,
      politique_annulation: form.politique_annulation,
    };
    try {
      onSaved(initial ? await modifierHebergement(initial.id, payload) : await creerHebergement(payload));
    } catch (err) {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data ?? {};
      const errs: Record<string, string> = {};
      for (const [k, v] of Object.entries(data)) {
        const msg = firstErrorMessage(v);
        if (msg) errs[k] = msg;
      }
      if (!Object.keys(errs).length) errs.detail = t("erreurEnregistrement");
      setErrors(errs);
      setSaving(false);
    }
  };

  const err = (k: string) => errors[k] && <p className="text-xs text-red-600 mt-1.5">{errors[k]}</p>;

  return (
    <form method="post" onSubmit={submit} className="space-y-5">
      {errors.detail && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-xl p-3">{errors.detail}</p>}

      <div>
        <label className={labelClass} htmlFor="h-name">{t("titre")}</label>
        <input id="h-name" className={inputClass} value={form.name} onChange={set("name")} placeholder={t("titreExemple")} required maxLength={200} />
        {err("name")}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className={labelClass} htmlFor="h-type">{t("type")}</label>
          <Select
            id="h-type" label={t("typeLogement")} value={form.type}
            onChange={(v) => setForm((prev) => ({ ...prev, type: v }))}
            options={(Object.keys(TYPE_LABELS) as HebergementType[]).map((id) => ({ value: id, label: TYPE_LABELS[id], hint: t(`types.${id}`) }))}
          />
        </div>
        <div>
          <p className={labelClass}>{t("capacite")}</p>
          <Stepper
            className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white"
            label={t("voyageursMax")} value={Number(form.max_guests) || 1} min={1} max={50}
            onChange={(n) => setForm((prev) => ({ ...prev, max_guests: String(n) }))}
          />
          {err("max_guests")}
        </div>
        <div>
          <label className={labelClass} htmlFor="h-city">{t("ville")}</label>
          <input id="h-city" className={inputClass} value={form.city} onChange={set("city")} placeholder="Lomé" required maxLength={100} />
          {err("city")}
        </div>
        <div>
          <label className={labelClass} htmlFor="h-location">{t("quartier")}</label>
          <input id="h-location" className={inputClass} value={form.location} onChange={set("location")} placeholder="Bè Kpota" maxLength={200} />
        </div>
        <div className="sm:col-span-2">
          <label className={labelClass} htmlFor="h-price">{t("prix")}</label>
          <input id="h-price" type="number" min={1} step={1} inputMode="numeric" className={inputClass} value={form.price_per_night} onChange={set("price_per_night")} placeholder="35000" required />
          {err("price_per_night")}
          {Number(form.price_per_night) > 0 && (
            <EstimateurRevenus className="mt-3 bg-gray-50" partenaire={revenus?.partenaire ?? "particulier"} prix={Number(form.price_per_night)} />
          )}
        </div>
      </div>

      <div>
        <p className={labelClass}>{t("position")}</p>
        <ChoixPosition valeur={position} onChange={setPosition} ville={form.city} />
        {err("latitude")}
      </div>

      <fieldset className="space-y-4">
        <legend className={labelClass}>{t("detailsTitre")}</legend>
        <p className="text-xs text-gray-500 -mt-1">{t("detailsAide")}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelClass} htmlFor="h-surface">{t("surface")}</label>
            <input id="h-surface" type="number" min={5} step={1} inputMode="numeric" className={inputClass} value={form.surface_m2}
              onChange={set("surface_m2")} placeholder="80" required />
            {err("surface_m2")}
          </div>
          <div className="space-y-2">
            <Stepper className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white" label={t("chambres")} value={form.chambres} min={0} max={50}
              onChange={(n) => setForm((prev) => ({ ...prev, chambres: n }))} />
            {err("chambres")}
            <Stepper className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white" label={t("sallesDeBain")} value={form.salles_de_bain} min={0} max={50}
              onChange={(n) => setForm((prev) => ({ ...prev, salles_de_bain: n }))} />
          </div>
        </div>
        <div>
          <p className={labelClass}>{t("lits")}</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {(["lits_doubles", "lits_simples", "canapes_lits"] as const).map((cle) => (
              <Stepper key={cle} className="border border-gray-200 rounded-xl px-4 py-2.5 bg-white"
                label={t(cle === "lits_doubles" ? "litsDoubles" : cle === "lits_simples" ? "litsSimples" : "canapesLits")}
                value={form[cle]} min={0} max={50} onChange={(n) => setForm((prev) => ({ ...prev, [cle]: n }))} />
            ))}
          </div>
          {err("lits")}
        </div>
        <div>
          <p className={labelClass} id="h-petitdej">{t("petitDejeuner")}</p>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-labelledby="h-petitdej">
            {(["inclus", "option", "non"] as const).map((v) => (
              <button key={v} type="button" role="radio" aria-checked={form.petit_dejeuner === v}
                onClick={() => setForm((prev) => ({ ...prev, petit_dejeuner: v }))}
                className={cn("relative zone-tactile px-4 py-2 rounded-full text-sm border transition-colors",
                  form.petit_dejeuner === v ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}>
                {t(v === "inclus" ? "petitDejInclus" : v === "option" ? "petitDejOption" : "petitDejNon")}
              </button>
            ))}
          </div>
          {err("petit_dejeuner")}
          {form.petit_dejeuner === "option" && (
            <div className="mt-3 sm:w-1/2">
              <label className={labelClass} htmlFor="h-petitdej-prix">{t("petitDejPrix")}</label>
              <input id="h-petitdej-prix" type="number" min={0} step={100} inputMode="numeric" className={inputClass}
                value={form.petit_dejeuner_prix} onChange={set("petit_dejeuner_prix")} placeholder="3000" required />
              {err("petit_dejeuner_prix")}
            </div>
          )}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass} htmlFor="h-arrivee">{t("arrivee")}</label>
            <input id="h-arrivee" type="time" className={inputClass} value={form.arrivee_a_partir} onChange={set("arrivee_a_partir")} />
          </div>
          <div>
            <label className={labelClass} htmlFor="h-depart">{t("depart")}</label>
            <input id="h-depart" type="time" className={inputClass} value={form.depart_avant} onChange={set("depart_avant")} />
          </div>
        </div>
        <div>
          <label className={labelClass} htmlFor="h-politique">{t("politique")}</label>
          <Select
            id="h-politique" label={t("politique")} value={form.politique_annulation}
            onChange={(v) => setForm((prev) => ({ ...prev, politique_annulation: v }))}
            options={POLITIQUES.map((id) => ({ value: id, label: tp(`${id}.nom`), hint: tp(`${id}.regle`) }))}
          />
          <p className="text-xs text-gray-500 mt-1.5">{t("politiqueAide")}</p>
          {err("politique_annulation")}
        </div>
      </fieldset>

      <div>
        <label className={labelClass} htmlFor="h-desc">{t("description")}</label>
        <textarea id="h-desc" rows={5} className={cn(inputClass, "resize-y")} value={form.description} onChange={set("description")} placeholder={t("descriptionPlaceholder")} />
      </div>

      <div>
        <p className={labelClass}>{t("photos")}</p>
        <p className="text-xs text-gray-500 -mt-1 mb-3">{t("photosAide")}</p>
        <PhotoUploader value={photos} onChange={onPhotosChange} onBusyChange={setUploading} error={errors.photos ?? errors.image_url ?? errors.images} />
        <div className="flex items-start gap-2 mt-4">
          <input
            type="checkbox" id="h-droits" checked={droitsPhotos} onChange={(e) => setDroitsPhotos(e.target.checked)}
            className="mt-1 accent-primary w-4 h-4 flex-shrink-0" aria-describedby={errors.droits ? "h-droits-erreur" : undefined}
          />
          <label htmlFor="h-droits" className="text-xs text-gray-600 leading-relaxed">
            {t.rich("certification", { cgu: (x) => <Link href="/cgu#hotes" target="_blank" className="text-primary underline">{x}<span className="sr-only"> ({t("nouvelOnglet")})</span></Link> })}
          </label>
        </div>
        {errors.droits && <p id="h-droits-erreur" role="alert" className="text-xs text-red-600 mt-1.5">{errors.droits}</p>}
      </div>

      <fieldset>
        <legend className={labelClass}>{t("equipements")}</legend>
        <div className="space-y-4">
          {CATEGORIES_EQUIPEMENTS.map((c) => (
            <div key={c.id}>
              <p className="text-xs text-gray-500 font-semibold mb-2">{c.label}</p>
              <div className="flex flex-wrap gap-2">
                {c.equipements.map(({ id, label, Icone }) => {
                  const active = form.amenities.includes(id);
                  return (
                    <button key={id} type="button" aria-pressed={active} onClick={() => toggleAmenity(id)}
                      className={cn("inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-sm border transition-colors", active ? "bg-primary text-white border-primary" : "bg-white text-dark border-gray-200 hover:border-primary/40")}>
                      <Icone size={18} weight="duotone" aria-hidden /> {label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className={labelClass}>{t("reglesMaison")}</legend>
        <p className="text-xs text-gray-500 -mt-1 mb-3">{t("reglesAide")}</p>
        <div className="space-y-3">
          {REGLES.map((r) => {
            const valeur = form.amenities.includes(r.oui.id) ? r.oui.id : form.amenities.includes(r.non.id) ? r.non.id : null;
            const options = [{ id: null, label: t("nonPrecise") }, { id: r.oui.id, label: r.oui.label }, { id: r.non.id, label: r.non.label }];
            return (
              <div key={r.id} className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                <span className="text-sm font-semibold text-dark sm:w-40 flex-shrink-0">{r.label}</span>
                <div role="radiogroup" aria-label={r.label} className="inline-flex flex-wrap rounded-xl border border-gray-200 bg-white p-1 gap-1">
                  {options.map((o) => (
                    <button key={o.id ?? "aucun"} type="button" role="radio" aria-checked={valeur === o.id} onClick={() => choisirRegle(r, o.id)}
                      className={cn("px-3 py-1.5 rounded-lg text-sm transition-colors", valeur === o.id ? "bg-primary text-white font-semibold" : "text-dark hover:bg-gray-50")}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </fieldset>

      <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-4 border-t border-gray-100">
        <button type="button" onClick={onCancel} className="px-6 py-3 rounded-xl border border-gray-200 text-dark font-medium hover:bg-gray-50">{t("annuler")}</button>
        <button type="submit" disabled={saving || uploading} className="px-8 py-3 bg-primary text-white rounded-xl font-bold shadow-md hover:bg-primary-600 disabled:opacity-60">
          {uploading ? t("envoiPhotos") : saving ? t("enregistrement") : initial ? t("enregistrerModifs") : t("publier")}
        </button>
      </div>
    </form>
  );
}
