import { useHomes } from "../api/hooks";
import { usePrefs } from "./prefs";

export function useCurrentHome() {
  const homes = useHomes();
  const { homeId } = usePrefs();
  const list = homes.data ?? [];
  const home = list.find((h) => h.id === homeId) ?? list[0];
  return { home, homes: list, isLoading: homes.isLoading, error: homes.error };
}
