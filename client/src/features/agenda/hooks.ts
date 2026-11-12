import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listAgents, listAppointments, readAgendaSettings, readPlanning, readTargetAppointment, listFreeSlots, listMoveSlots, readAppointment, readAvailability, readCoverage,
  readFeed, readMyVisit,
} from "./api";

export const agendaKeys = {
  all: ["agenda"] as const,
  availability: () => [...agendaKeys.all, "availability"] as const,
  appointments: (start: string, end: string, agent: string) => [...agendaKeys.all, "appointments", start, end, agent] as const,
  appointment: (id: string) => [...agendaKeys.all, "appointment", id] as const,
  targetAppointment: (targetId: string) => [...agendaKeys.all, "target-appointment", targetId] as const,
  feed: () => [...agendaKeys.all, "feed"] as const,
  coverage: () => [...agendaKeys.all, "coverage"] as const,
  agents: () => [...agendaKeys.all, "agents"] as const,
  settings: () => [...agendaKeys.all, "settings"] as const,
  planning: (day: string, city: string) => [...agendaKeys.all, "planning", day, city] as const,
  myVisit: () => [...agendaKeys.all, "my-visit"] as const,
  freeSlots: (listingIds: string[]) => [...agendaKeys.all, "free-slots", ...listingIds] as const,
  moveSlots: (appointmentId: string) => [...agendaKeys.all, "move-slots", appointmentId] as const,
};

export function useAvailability() {
  return useQuery({ queryKey: agendaKeys.availability(), queryFn: readAvailability });
}

export function useAppointments(start: string, end: string, agent = "") {
  return useQuery({
    queryKey: agendaKeys.appointments(start, end, agent),
    queryFn: () => listAppointments({ start, end, ...(agent ? { agent } : {}) }),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export function useAppointment(id: string) {
  return useQuery({ queryKey: agendaKeys.appointment(id), queryFn: () => readAppointment(id), enabled: !!id });
}

export function useFeed() {
  return useQuery({ queryKey: agendaKeys.feed(), queryFn: readFeed });
}

export function useCoverage(enabled = true) {
  return useQuery({ queryKey: agendaKeys.coverage(), queryFn: readCoverage, enabled });
}

export function useAgents(enabled = true) {
  return useQuery({ queryKey: agendaKeys.agents(), queryFn: listAgents, enabled, staleTime: 5 * 60_000 });
}

export function useMyVisit() {
  return useQuery({ queryKey: agendaKeys.myVisit(), queryFn: readMyVisit });
}

export function useFreeSlots(listingIds: string[]) {
  return useQuery({
    queryKey: agendaKeys.freeSlots(listingIds),
    queryFn: () => listFreeSlots(listingIds),
    enabled: listingIds.length > 0,
  });
}

export function useMoveSlots(appointmentId: string | null) {
  return useQuery({
    queryKey: agendaKeys.moveSlots(appointmentId ?? ""),
    queryFn: () => listMoveSlots(appointmentId ?? ""),
    enabled: !!appointmentId,
  });
}

export function useAgendaMutation<T, R>(action: (value: T) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: agendaKeys.all }),
  });
}

export function useAgendaSettings() {
  return useQuery({ queryKey: agendaKeys.settings(), queryFn: readAgendaSettings });
}

export function useTargetAppointment(targetId: string) {
  return useQuery({ queryKey: agendaKeys.targetAppointment(targetId), queryFn: () => readTargetAppointment(targetId) });
}

export function usePlanning(day: string, city: string) {
  return useQuery({
    queryKey: agendaKeys.planning(day, city),
    queryFn: () => readPlanning(day, city),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}
