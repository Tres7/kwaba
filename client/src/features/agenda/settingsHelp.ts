import { formatDuration } from "./time";
import type { AgendaSettingsValues } from "./types";

export type SettingKey = keyof AgendaSettingsValues;
export type SettingKind = "duration" | "number";

export interface SettingField {
  key: SettingKey;
  label: string;
  kind: SettingKind;
  unit?: (value: number) => string;
  help: (values: AgendaSettingsValues) => string;
}

const WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"];

const plural = (count: number, word: string) => `${count} ${word}${count > 1 ? "s" : ""}`;

export function clock(totalMinutes: number): string {
  const minutes = ((totalMinutes % 1440) + 1440) % 1440;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${String(rest).padStart(2, "0")}` : `${hours} h`;
}

export function afterMonday10(hours: number): string {
  const total = 10 + hours;
  const day = Math.floor(total / 24);
  const prefix = day === 0 ? "le lundi" : day < 7 ? `le ${WEEKDAYS[day]}` : `le ${WEEKDAYS[day % 7]} suivant`;
  return `${prefix} à ${clock((total % 24) * 60)}`;
}

function dayAfterMonday(days: number): string {
  if (days < 7) return `le ${WEEKDAYS[days]}`;
  return `le ${WEEKDAYS[days % 7]} de la semaine suivante`;
}

export const SECTIONS: { title: string; fields: SettingField[] }[] = [
  {
    title: "Réservation par l'hôte",
    fields: [
      {
        key: "notice_hours", label: "Préavis", kind: "number", unit: () => "h",
        help: (v) => `Un hôte ne peut pas réserver une visite à moins de ${v.notice_hours} h. S'il réserve le lundi à 10 h, le premier créneau proposé est ${afterMonday10(v.notice_hours)}. L'agent a ainsi le temps de s'organiser, et la visite figure dans son récapitulatif de la veille.`,
      },
      {
        key: "horizon_days", label: "Horizon de réservation", kind: "number", unit: (v) => (v > 1 ? "jours" : "jour"),
        help: (v) => `L'hôte voit les créneaux des ${plural(v.horizon_days, "jour")} à venir. S'il réserve aujourd'hui, la visite peut être fixée au plus tard dans ${plural(v.horizon_days, "jour")}. Les agents n'ont pas à publier leurs disponibilités plus loin.`,
      },
      {
        key: "max_per_day", label: "Visites maximum par jour", kind: "number", unit: (v) => (v > 1 ? "visites" : "visite"),
        help: (v) => `Un agent reçoit au plus ${plural(v.max_per_day, "visite")} par jour. Une visite groupée (plusieurs annonces sur le même site) compte pour une seule. L'agent peut relever sa limite pour une date précise, jusqu'à 10.`,
      },
    ],
  },
  {
    title: "Durées",
    fields: [
      {
        key: "visit_minutes", label: "Durée d'une visite", kind: "duration",
        help: (v) => `Une visite qui commence à 9 h se termine à ${clock(9 * 60 + v.visit_minutes)}. C'est la durée réservée dans l'agenda de l'agent pour une annonce.`,
      },
      {
        key: "extra_listing_minutes", label: "Supplément par annonce groupée", kind: "duration",
        help: (v) => `Pour une visite groupée, chaque annonce en plus ajoute ce temps. Trois chambres d'un même hôtel : ${formatDuration(v.visit_minutes + 2 * v.extra_listing_minutes)} de visite.`,
      },
      {
        key: "margin_minutes", label: "Écart entre deux visites", kind: "duration",
        help: (v) => v.margin_minutes === 0
          ? "Aucun écart : après une visite qui finit à 10 h, la suivante peut commencer à 10 h. Prévoyez du temps de trajet !"
          : `Temps de trajet laissé à l'agent. Après une visite qui finit à 10 h, la suivante commence au plus tôt à ${clock(600 + v.margin_minutes)}. Pas d'écart après la dernière visite de la journée. Les visites déjà réservées gardent leur écart.`,
      },
    ],
  },
  {
    title: "Visites groupées",
    fields: [
      {
        key: "max_listings", label: "Annonces maximum par visite", kind: "number", unit: (v) => (v > 1 ? "annonces" : "annonce"),
        help: (v) => `Un hôte peut regrouper au plus ${plural(v.max_listings, "annonce")} dans une même visite, soit ${formatDuration(v.visit_minutes + (v.max_listings - 1) * v.extra_listing_minutes)} au plus.`,
      },
      {
        key: "same_site_distance_m", label: "Distance « même site »", kind: "number", unit: () => "m",
        help: (v) => `Des annonces peuvent être visitées ensemble si elles sont toutes à moins de ${v.same_site_distance_m} m les unes des autres (environ ${Math.max(1, Math.round(v.same_site_distance_m / 80))} min à pied). Au-delà, l'hôte réserve une visite par annonce.`,
      },
    ],
  },
  {
    title: "Rappels et alertes",
    fields: [
      {
        key: "digest_hour", label: "Heure du récapitulatif de la veille", kind: "number", unit: () => "h",
        help: (v) => `À partir de ${v.digest_hour} h, chaque agent reçoit la liste de ses visites du lendemain, et chaque hôte un rappel de sa visite.`,
      },
      {
        key: "decision_alert_hours", label: "Alerte « visite sans décision »", kind: "number", unit: () => "h",
        help: (v) => `Une visite qui finit à 10 h sans décision de l'agent déclenche une alerte aux admins à ${clock((10 + v.decision_alert_hours) * 60)}${10 + v.decision_alert_hours >= 24 ? " (un autre jour)" : ""}.`,
      },
      {
        key: "host_reminder_days", label: "Relance de l'hôte sans réservation", kind: "number", unit: (v) => (v > 1 ? "jours" : "jour"),
        help: (v) => `Un hôte invité le lundi à réserver sa visite, qui ne l'a pas fait, reçoit une relance ${dayAfterMonday(v.host_reminder_days)}.`,
      },
      {
        key: "host_alert_days", label: "Alerte aux admins", kind: "number", unit: (v) => (v > 1 ? "jours" : "jour"),
        help: (v) => `Toujours sans réservation, les admins sont alertés ${dayAfterMonday(v.host_alert_days)}, avec le téléphone de l'hôte et les villes sans créneau libre. Doit venir après la relance de l'hôte.`,
      },
    ],
  },
];

export function durationOptions(min: number, max: number): number[] {
  const options: number[] = [];
  for (let value = min; value <= max; value += 5) options.push(value);
  return options;
}
