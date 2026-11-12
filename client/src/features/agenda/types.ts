export type AppointmentStatus = "confirmed" | "cancelled" | "done";

export interface ListingRef {
  id: string;
  title: string;
}

export interface Appointment {
  id: string;
  title: string;
  city: string;
  address: string;
  start: string;
  end: string;
  status: AppointmentStatus;
  origin: "host" | "phone";
  on_the_way_at: string | null;
  listings: ListingRef[];
  agent: { id: string; name: string } | null;
  cancellation_reason: string;
  closing_reason: string;
  post_check: boolean;
}

export interface TargetAppointment extends Appointment {
  mine: boolean;
}

export interface AppointmentDetail extends Appointment {
  position: { latitude: number; longitude: number } | null;
  host: { name: string; phone: string; email: string } | null;
}

export interface WeeklySlot {
  weekday: number;
  start: string;
  end: string;
}

export interface AvailabilityException {
  id: number;
  day: string;
  kind: "block" | "extra";
  start: string | null;
  end: string | null;
}

export interface Availability {
  timezone: string;
  cities: string[];
  weekly_slots: WeeklySlot[];
  exceptions: AvailabilityException[];
  day_limits: { day: string; max_visits: number }[];
  rules: {
    visit_duration_min: number;
    margin_min: number;
    max_per_day: number;
    per_day_ceiling: number;
    notice_h: number;
    horizon_days: number;
  };
}

export interface CityCoverage {
  city: string;
  agents: { id: string; name: string }[];
  free_slots: number;
  upcoming_visits: number;
}

export interface DelayStats {
  count: number;
  median_h: number | null;
  mean_h: number | null;
}

export interface Coverage {
  cities: CityCoverage[];
  delays: {
    days: number;
    listing_to_booking: DelayStats;
    booking_to_visit: DelayStats;
    visit_to_decision: DelayStats;
    by_phone: number;
    total: number;
  };
}

export interface AgentRef {
  id: string;
  name: string;
  role: string;
}

export interface HostAppointment {
  id: string;
  agent_id: string;
  listings: ListingRef[];
  city: string;
  start: string;
  end: string;
  status: AppointmentStatus;
  origin: "host" | "phone";
  on_the_way_at: string | null;
  movable: boolean;
}

export interface ListingToSchedule {
  id: string;
  name: string;
  city: string;
  address: string;
  image_url: string | null;
  has_position: boolean;
  appointment: HostAppointment | null;
}

export interface MyVisit {
  listings: ListingToSchedule[];
  rules: {
    visit_duration_min: number;
    extra_listing_min: number;
    max_listings: number;
    notice_h: number;
    horizon_days: number;
    same_site_distance_m: number;
  };
}

export interface AgendaSettingsValues {
  notice_hours: number;
  horizon_days: number;
  max_per_day: number;
  margin_minutes: number;
  visit_minutes: number;
  extra_listing_minutes: number;
  max_listings: number;
  same_site_distance_m: number;
  digest_hour: number;
  decision_alert_hours: number;
  host_reminder_days: number;
  host_alert_days: number;
}

export interface AgendaSettings {
  values: AgendaSettingsValues;
  defaults: AgendaSettingsValues;
  bounds: Record<keyof AgendaSettingsValues, { min: number; max: number }>;
  updated_at: string | null;
  updated_by: string | null;
}

export interface TimeRange {
  start: string;
  end: string;
}

export interface PlanningAppointment {
  id: string;
  title: string;
  city: string;
  address: string;
  start: string;
  end: string;
  status: AppointmentStatus;
  origin: "host" | "phone";
  on_the_way_at: string | null;
  post_check: boolean;
}

export interface AgentPlan {
  id: string;
  name: string;
  role: string;
  cities: string[];
  max_visits: number;
  visits: number;
  windows: TimeRange[];
  blocks: TimeRange[];
  appointments: PlanningAppointment[];
}

export interface Planning {
  day: string;
  city: string;
  timezone: string;
  cities: string[];
  agents: AgentPlan[];
}
