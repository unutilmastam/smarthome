import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { Command, Device, Home, Hub, Member, Room, SessionInfo } from "./types";

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
