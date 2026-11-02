"use client";

import { creerType, listerTypes, modifierType, supprimerType } from "./api";
import { clesHebergements, useHebergementHote } from "./hooks";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BedDouble, Eye, EyeOff, Pencil, Plus, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import PhotoUploader from "./PhotoUploader";
import SubPageHeader from "@/components/layout/SubPageHeader";
import type { TypeLogement } from "@/types/api/models";
import { useTranslations } from "next-intl";
import { useFormat } from "@/lib/format";

type Brouillon = Pick<TypeLogement, "nom" | "description" | "photos"> & { capacite: string; prix_nuit: string; quantite: string };

const VIDE: Brouillon = { nom: "", description: "", photos: [], capacite: "2", prix_nuit: "", quantite: "1" };

function brouillonDe(u: TypeLogement): Brouillon {
  return { nom: u.nom, description: u.description, photos: u.photos, capacite: String(u.capacite),
    prix_nuit: String(Math.round(Number(u.prix_nuit))), quantite: String(u.quantite) };
}

export default function TypesLogementPage() {
  const { formatPrice } = useFormat();
  const t = useTranslations("typesHote");
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  // Type being edited: its id, "nouveau" for a new one, or nothing
  const [edition, setEdition] = useState<string | null>(null);

  const { data: hebergement } = useHebergementHote(id);
  const { data: types = [], isLoading } = useQuery({
    queryKey: clesHebergements.types(id),
    queryFn: () => listerTypes(id),
  });

  // The listing's "from" price and capacity follow its types
  const rafraichir = () => {
    queryClient.invalidateQueries({ queryKey: clesHebergements.types(id) });
    queryClient.invalidateQueries({ queryKey: clesHebergements.fiche(id) });
    queryClient.invalidateQueries({ queryKey: clesHebergements.mes });
  };

  const basculer = async (u: TypeLogement) => {
    try {
      await modifierType(u.id, { actif: !u.actif });
      toast.success(u.actif ? t("desactive") : t("reactive"));
      rafraichir();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const supprimer = async (u: TypeLogement) => {
    if (!window.confirm(t("supprimerQuestion", { nom: u.nom }))) return;
    try {
      await supprimerType(u.id);
      toast.success(t("supprime"));
      rafraichir();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 md:py-12">
      <SubPageHeader title={t("titre")} subtitle={hebergement?.name ?? "…"} back="/hote/espace" />
      <p className="text-sm text-gray-600 mb-6">{t("aide")}</p>

      {isLoading ? <div className="h-40 skeleton rounded-3xl" /> : (
        <div className="space-y-4">
          {types.map((u) => edition === u.id ? (
            <FormulaireType key={u.id} hebergementId={id} type={u} onFin={() => { setEdition(null); rafraichir(); }} onAnnuler={() => setEdition(null)} />
          ) : (
            <article key={u.id} className={cn("bg-white rounded-3xl shadow-card p-5", u.actif === false && "opacity-60")}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="font-heading font-bold text-dark flex items-center gap-2">
                    <BedDouble size={16} className="text-primary flex-shrink-0" /> <span className="truncate">{u.nom}</span>
                    {u.actif === false && <span className="text-[11px] font-semibold bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">{t("inactif")}</span>}
                  </h2>
                  <p className="text-sm text-gray-600 mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    <span>{t("quantiteNombre", { nombre: u.quantite })}</span>
                    <span className="flex items-center gap-1"><Users size={13} /> {t("capaciteNombre", { nombre: u.capacite })}</span>
                  </p>
                </div>
                <p className="font-bold text-dark whitespace-nowrap">{formatPrice(u.prix_nuit)}<span className="text-xs font-normal text-gray-500"> {t("parNuit")}</span></p>
              </div>
              {u.description && <p className="text-sm text-gray-600 mt-2 line-clamp-2">{u.description}</p>}
              <div className="flex flex-wrap gap-2 mt-4">
                <button onClick={() => setEdition(u.id)} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gray-100 text-dark text-sm font-medium hover:bg-gray-200"><Pencil size={14} /> {t("modifier")}</button>
                <button onClick={() => basculer(u)} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gray-100 text-dark text-sm font-medium hover:bg-gray-200">
                  {u.actif === false ? <><Eye size={14} /> {t("reactiver")}</> : <><EyeOff size={14} /> {t("desactiver")}</>}
                </button>
                <button onClick={() => supprimer(u)} className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-red-50 text-red-700 text-sm font-medium hover:bg-red-100"><Trash2 size={14} /> {t("supprimer")}</button>
              </div>
            </article>
          ))}

          {edition === "nouveau" ? (
            <FormulaireType hebergementId={id} onFin={() => { setEdition(null); rafraichir(); }} onAnnuler={() => setEdition(null)} />
          ) : (
            <button onClick={() => setEdition("nouveau")}
              className="w-full flex items-center justify-center gap-2 py-4 rounded-3xl border-2 border-dashed border-gray-200 text-primary font-semibold hover:border-primary/50">
              <Plus size={18} /> {t("ajouter")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function FormulaireType({ hebergementId, type, onFin, onAnnuler }: {
  hebergementId: string; type?: TypeLogement; onFin: () => void; onAnnuler: () => void;
}) {
  const t = useTranslations("typesHote");
  const [b, setB] = useState<Brouillon>(() => (type ? brouillonDe(type) : VIDE));
  const [photosOccupees, setPhotosOccupees] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const maj = (champ: keyof Brouillon) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setB({ ...b, [champ]: e.target.value });

  const enregistrer = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    const donnees = { nom: b.nom.trim(), description: b.description.trim(), photos: b.photos,
      capacite: Number(b.capacite), prix_nuit: Number(b.prix_nuit), quantite: Number(b.quantite) };
    try {
      if (type) await modifierType(type.id, donnees);
      else await creerType(hebergementId, donnees);
      toast.success(type ? t("enregistre") : t("ajoute"));
      onFin();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setEnvoi(false);
    }
  };

  const champ = "w-full border border-gray-200 rounded-xl px-3 py-2.5 text-base sm:text-sm outline-none focus:border-primary";
  return (
    <form onSubmit={enregistrer} className="bg-white rounded-3xl shadow-card p-5 space-y-4">
      <h2 className="font-heading font-bold text-dark">{type ? t("modifierTitre") : t("ajouter")}</h2>
      <label className="block">
        <span className="text-sm font-medium text-dark">{t("nom")}</span>
        <input required maxLength={120} value={b.nom} onChange={maj("nom")} placeholder={t("nomExemple")} className={cn(champ, "mt-1")} />
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label className="block">
          <span className="text-sm font-medium text-dark">{t("prix")}</span>
          <input required type="number" inputMode="numeric" min={1} value={b.prix_nuit} onChange={maj("prix_nuit")} className={cn(champ, "mt-1")} />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-dark">{t("quantite")}</span>
          <input required type="number" inputMode="numeric" min={1} max={500} value={b.quantite} onChange={maj("quantite")} className={cn(champ, "mt-1")} />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-dark">{t("capacite")}</span>
          <input required type="number" inputMode="numeric" min={1} max={50} value={b.capacite} onChange={maj("capacite")} className={cn(champ, "mt-1")} />
        </label>
      </div>
      <p className="text-xs text-gray-500">{t("quantiteAide")}</p>
      <label className="block">
        <span className="text-sm font-medium text-dark">{t("description")}</span>
        <textarea rows={3} maxLength={2000} value={b.description} onChange={maj("description")} className={cn(champ, "mt-1 resize-y")} />
      </label>
      <div>
        <span className="text-sm font-medium text-dark">{t("photos")}</span>
        <p className="text-xs text-gray-500 mb-2">{t("photosAide")}</p>
        <PhotoUploader value={b.photos} onChange={(photos) => setB((x) => ({ ...x, photos }))} onBusyChange={setPhotosOccupees} />
      </div>
      <div className="flex gap-2">
        <button type="button" onClick={onAnnuler} className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-medium">{t("annuler")}</button>
        <button type="submit" disabled={envoi || photosOccupees} className="flex-1 py-2.5 rounded-xl bg-primary text-white text-sm font-bold disabled:opacity-50">
          {envoi ? "..." : t("enregistrer")}
        </button>
      </div>
    </form>
  );
}
