"use client";

import { suggererDestinations } from "./api";
import { useVilles } from "./hooks";
import { Fragment, useId, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Building2, Home, MapPin } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useDebounced } from "@/lib/useAdminList";
import { cn } from "@/lib/utils";
import { QUARTIERS_LOME, quartiersCorrespondants } from "@/lib/quartiers";

export interface Suggestions {
  villes: { city: string; count: number }[];
  logements: { id: string; name: string; city: string; image_url: string }[];
}

type Option =
  | { type: "ville"; city: string; count: number }
  | { type: "quartier"; nom: string }
  | { type: "logement"; id: string; name: string; city: string; image_url: string };

interface ChampDestinationProps {
  value: string;
  onChange: (valeur: string) => void;
  /** City chosen in the list (the parent starts the search or keeps the city for the rest of the form). */
  onVille: (ville: string) => void;
  /** Called after a suggested listing is opened. */
  onLogement?: () => void;
  placeholder?: string;
  ariaLabel?: string;
  type?: "text" | "search";
  inputRef?: React.Ref<HTMLInputElement>;
  className?: string;
  inputClassName?: string;
  /** Position of the list under the field (width, alignment). */
  listeClassName?: string;
}

/** "Destination" field with suggestions while typing: cities ("lome" finds "Lomé"), Lomé districts, then listings. */
export default function ChampDestination({
  value, onChange, onVille, onLogement, placeholder, ariaLabel, type = "text", inputRef, className, inputClassName, listeClassName,
}: ChampDestinationProps) {
  const t = useTranslations("suggestions");
  const router = useRouter();
  const id = useId();
  const [ouvert, setOuvert] = useState(false);
  const [actif, setActif] = useState(-1);

  const saisie = useDebounced(value.trim(), 200);
  const { data: trouvees } = useQuery({
    queryKey: ["suggestions", saisie],
    queryFn: () => suggererDestinations(saisie),
    enabled: ouvert && saisie.length > 0,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
  // Empty field: popular destinations (same request as the home page, so often already cached)
  const { data: populaires = [] } = useVilles(ouvert && !value.trim());

  const options: Option[] = value.trim()
    ? [
        ...(trouvees?.villes ?? []).map((v) => ({ type: "ville" as const, ...v })),
        ...quartiersCorrespondants(value).slice(0, 6).map((nom) => ({ type: "quartier" as const, nom })),
        ...(trouvees?.logements ?? []).map((l) => ({ type: "logement" as const, ...l })),
      ]
    : [
        ...populaires.slice(0, 6).map((v) => ({ type: "ville" as const, city: v.city, count: v.count })),
        ...QUARTIERS_LOME.slice(0, 8).map((nom) => ({ type: "quartier" as const, nom })),
      ];
  const visible = ouvert && options.length > 0;

  const choisir = (option: Option) => {
    setOuvert(false);
    setActif(-1);
    if (option.type === "ville" || option.type === "quartier") {
      const lieu = option.type === "ville" ? option.city : option.nom;
      onChange(lieu);
      onVille(lieu);
    } else {
      router.push(`/hebergements/${option.id}`);
      onLogement?.();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!options.length) return;
      e.preventDefault();
      setOuvert(true);
      const pas = e.key === "ArrowDown" ? 1 : -1;
      // -1 = back to the typed text, then wrap around
      setActif((i) => {
        const suivant = i + pas;
        return suivant < -1 ? options.length - 1 : suivant >= options.length ? -1 : suivant;
      });
    } else if (e.key === "Enter" && visible && actif >= 0 && actif < options.length) {
      // Suggestion highlighted with the keyboard: it is chosen instead of submitting the form
      e.preventDefault();
      choisir(options[actif]);
    } else if (e.key === "Escape" && visible) {
      e.preventDefault();
      setOuvert(false);
    }
  };

  const titres = { ville: value.trim() ? t("villes") : t("populaires"), quartier: t("quartiers"), logement: t("logements") };
  const titre = (texte: string) => <li role="presentation" className="px-4 pt-3 pb-1 text-[11px] font-bold uppercase tracking-wide text-gray-400">{texte}</li>;

  return (
    <div className={cn("relative", className)}>
      <input
        ref={inputRef}
        type={type}
        value={value}
        onChange={(e) => { onChange(e.target.value); setOuvert(true); setActif(-1); }}
        onFocus={() => setOuvert(true)}
        onBlur={() => setOuvert(false)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        aria-label={ariaLabel}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={visible}
        aria-controls={`${id}-liste`}
        aria-activedescendant={visible && actif >= 0 && actif < options.length ? `${id}-${actif}` : undefined}
        autoComplete="off"
        className={inputClassName}
      />
      {visible && (
        <ul
          id={`${id}-liste`}
          role="listbox"
          aria-label={ariaLabel}
          // Keeps the focus in the field: otherwise the blur would close the list before the click
          onMouseDown={(e) => e.preventDefault()}
          className={cn("absolute top-full z-50 mt-3 max-h-[70vh] overflow-y-auto rounded-2xl border border-gray-100 bg-white pb-2 text-left shadow-card", listeClassName ?? "left-0 w-full min-w-[18rem]")}
        >
          {options.map((option, index) => (
            <Fragment key={option.type === "ville" ? `v-${option.city}` : option.type === "quartier" ? `q-${option.nom}` : `l-${option.id}`}>
              {options[index - 1]?.type !== option.type && titre(titres[option.type])}
              <li
                id={`${id}-${index}`}
                role="option"
                aria-selected={index === actif}
                onClick={() => choisir(option)}
                onMouseEnter={() => setActif(index)}
                className={cn("mx-2 flex cursor-pointer items-center gap-3 rounded-xl px-2 py-2", index === actif && "bg-primary/5")}
              >
                {option.type === "ville" ? (
                  <>
                    <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 text-primary"><MapPin size={16} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-dark">{option.city}</span>
                      <span className="block text-xs text-gray-500">{t("logementsDispo", { nombre: option.count })}</span>
                    </span>
                  </>
                ) : option.type === "quartier" ? (
                  <>
                    <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 text-primary"><MapPin size={16} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-dark">{option.nom}</span>
                      <span className="block text-xs text-gray-500">{t("quartierLome")}</span>
                    </span>
                  </>
                ) : (
                  <>
                    {option.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={option.image_url} alt="" className="h-9 w-9 flex-shrink-0 rounded-lg object-cover" />
                    ) : (
                      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-400"><Home size={16} /></span>
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-dark">{option.name}</span>
                      <span className="flex items-center gap-1 text-xs text-gray-500"><Building2 size={12} /> {option.city}</span>
                    </span>
                  </>
                )}
              </li>
            </Fragment>
          ))}
        </ul>
      )}
    </div>
  );
}
