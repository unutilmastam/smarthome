import { create } from "zustand";
import { useTranslation } from "react-i18next";
import type { Room } from "../api/types";
import { useDevices, useRooms } from "../api/hooks";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";
import { AddDeviceSheet, AddMenuSheet, RoomSheet } from "./AddForms";
import { Icon } from "./Icon";

type Mode = null | "menu" | "device" | "room";
/** Start the device form on a given type, e.g. a breaker in a given panel slot (ADR 0015). */
export interface DevicePreset { type: string; panel?: string; position?: number }
interface AddFlow {
  mode: Mode; room?: Room; defaultRoom: string; preset?: DevicePreset;
  open: (mode: Exclude<Mode, null>, opts?: { room?: Room; defaultRoom?: string; preset?: DevicePreset }) => void;
  close: () => void;
}

/** One place that owns the "add device / add room / edit room" sheets. */
export const useAddFlow = create<AddFlow>((set) => ({
  mode: null, defaultRoom: "",
  open: (mode, opts) => set({ mode, room: opts?.room, defaultRoom: opts?.defaultRoom ?? "", preset: opts?.preset }),
  close: () => set({ mode: null, room: undefined, preset: undefined }),
}));

/** Can the current user add/edit devices and rooms? */
export function useCanConfigure() {
  const { home } = useCurrentHome();
  return !!home && can(home.my_role, "configure");
}

export function AddButton({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation();
  const open = useAddFlow((s) => s.open);
  if (!useCanConfigure()) return null;
  return (
    <button type="button" className={compact ? "icon-btn accent" : "primary add-btn"} aria-label={t("add.title")}
      onClick={() => open("menu")}>
      <Icon name="plus" size={20} />{!compact && <span>{t("app.add")}</span>}
    </button>
  );
}

export function AddFlowHost() {
  const { home } = useCurrentHome();
  const { mode, room, defaultRoom, preset, open, close } = useAddFlow();
  const rooms = useRooms(home?.id);
  const devices = useDevices(home?.id, true);
  if (!home || !can(home.my_role, "configure")) return null;
  return (
    <>
      <AddMenuSheet open={mode === "menu"} onClose={close} onDevice={() => open("device")} onRoom={() => open("room")} />
      <AddDeviceSheet open={mode === "device"} onClose={close} homeId={home.id} rooms={rooms.data ?? []}
        devices={devices.data ?? []} defaultRoom={defaultRoom} preset={preset} />
      <RoomSheet open={mode === "room"} onClose={close} homeId={home.id} room={room} />
    </>
  );
}
