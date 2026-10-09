import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { AppNotification, Automation, AutomationRun, Command, Device, EnergySummary, Home, HomeEvent, Hub, Member, Room, SessionInfo, NotificationChannels, NotifyPrefs, TelemetryPoint } from "./types";

/** Device state refresh when realtime is not available (ARCHITECTURE 2.A: 3 s). */
export const POLL_MS = 3000;

export const qk = {
  homes: ["homes"] as const,
  devices: (home: string) => ["devices", home] as const,
  device: (id: string) => ["device", id] as const,
  rooms: (home: string) => ["rooms", home] as const,
  hubs: (home: string) => ["hubs", home] as const,
  members: (home: string) => ["members", home] as const,
  commands: (device: string) => ["commands", device] as const,
  sessions: ["sessions"] as const,
};

export const useHomes = () => useQuery({ queryKey: qk.homes, queryFn: () => api.get<Home[]>("/homes") });

export const useDevices = (home?: string, realtime = false) =>
  useQuery({
    queryKey: qk.devices(home ?? ""), enabled: !!home,
    queryFn: () => api.get<Device[]>(`/homes/${home}/devices?limit=200`),
    refetchInterval: realtime ? false : POLL_MS,
  });

export const useDevice = (id?: string, realtime = false) =>
  useQuery({
    queryKey: qk.device(id ?? ""), enabled: !!id,
    queryFn: () => api.get<Device>(`/devices/${id}`),
    refetchInterval: realtime ? false : POLL_MS,
  });

export const useRooms = (home?: string) =>
  useQuery({ queryKey: qk.rooms(home ?? ""), enabled: !!home, queryFn: () => api.get<Room[]>(`/homes/${home}/rooms`) });

export const useHubs = (home?: string) =>
  useQuery({ queryKey: qk.hubs(home ?? ""), enabled: !!home, queryFn: () => api.get<Hub[]>(`/homes/${home}/hubs`), refetchInterval: 15000 });

export const useMembers = (home?: string, enabled = true) =>
  useQuery({ queryKey: qk.members(home ?? ""), enabled: !!home && enabled, queryFn: () => api.get<Member[]>(`/homes/${home}/members`) });

export const useDeviceCommands = (device?: string) =>
  useQuery({ queryKey: qk.commands(device ?? ""), enabled: !!device, queryFn: () => api.get<Command[]>(`/devices/${device}/commands?limit=50`), refetchInterval: POLL_MS });

export const useSessions = () => useQuery({ queryKey: qk.sessions, queryFn: () => api.get<SessionInfo[]>("/auth/sessions") });

export const useEnergy = (home?: string, period: "day" | "month" = "day") =>
  useQuery({ queryKey: ["energy", home ?? "", period], enabled: !!home, refetchInterval: 60_000,
    queryFn: () => api.get<EnergySummary>(`/homes/${home}/energy/summary?period=${period}`) });

export const useTelemetry = (device?: string, metric = "power_meter.power", hours = 6) =>
  useQuery({ queryKey: ["telemetry", device ?? "", metric, hours], enabled: !!device, refetchInterval: 60_000,
    queryFn: () => api.get<TelemetryPoint[]>(`/devices/${device}/telemetry?metric=${metric}&resolution=1m&hours=${hours}`) });

/** Event feed (ADR 0012). Refreshed every 10 s; newest first. */
export const useEvents = (home?: string, filter: { severity?: string; capability?: string; device_id?: string; limit?: number } = {}) => {
  const qs = new URLSearchParams({ limit: String(filter.limit ?? 50) });
  if (filter.severity) qs.set("severity", filter.severity);
  if (filter.capability) qs.set("capability", filter.capability);
  if (filter.device_id) qs.set("device_id", filter.device_id);
  return useQuery({ queryKey: ["events", home ?? "", qs.toString()], enabled: !!home, refetchInterval: 10_000,
    queryFn: () => api.get<HomeEvent[]>(`/homes/${home}/events?${qs}`) });
};

export const useAutomations = (home?: string) =>
  useQuery({ queryKey: ["automations", home ?? ""], enabled: !!home, refetchInterval: 15_000,
    queryFn: () => api.get<Automation[]>(`/homes/${home}/automations`) });

export const useAutomationRuns = (id?: string) =>
  useQuery({ queryKey: ["automation-runs", id ?? ""], enabled: !!id, refetchInterval: 10_000,
    queryFn: () => api.get<AutomationRun[]>(`/automations/${id}/runs?limit=50`) });

/** Notifications (ADR 0014). meta.unacked = warning/critical nobody has acknowledged yet. */
export const useNotifications = (home?: string, unacked = false, limit = 100) =>
  useQuery({ queryKey: ["notifications", home ?? "", unacked, limit], enabled: !!home, refetchInterval: 15_000,
    queryFn: async () => {
      const r = await api.page<AppNotification[]>(`/homes/${home}/notifications?limit=${limit}${unacked ? "&unacked=true" : ""}`);
      return { items: r.data, unacked: Number(r.meta.unacked ?? 0) };
    } });

export const useNotificationChannels = () =>
  useQuery({ queryKey: ["notification-channels"], queryFn: () => api.get<NotificationChannels>("/notifications/settings") });

export const useNotifyPrefs = (home?: string) =>
  useQuery({ queryKey: ["notify-prefs", home ?? ""], enabled: !!home,
    queryFn: () => api.get<NotifyPrefs>(`/homes/${home}/notification-prefs`) });
