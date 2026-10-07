import { create } from "zustand";

/** Per-device UI preferences only (no secrets, no device state). */
function load<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v ? (JSON.parse(v) as T) : fallback; }
  catch { return fallback; }
}
function save(key: string, v: unknown) { try { localStorage.setItem(key, JSON.stringify(v)); } catch { /* ignore */ } }

interface Prefs {
  homeId: string | null;
  theme: "system" | "light" | "dark";
  pinned: Record<string, string[]>;
  setHome: (id: string) => void;
  setTheme: (t: Prefs["theme"]) => void;
  togglePin: (home: string, device: string) => void;
}

export const usePrefs = create<Prefs>((set, get) => ({
  homeId: load("sh.home", null),
  theme: load("sh.theme", "system"),
  pinned: load("sh.pinned", {}),
  setHome: (id) => { save("sh.home", id); set({ homeId: id }); },
  setTheme: (theme) => {
    save("sh.theme", theme);
    applyTheme(theme);
    set({ theme });
  },
  togglePin: (home, device) => {
    const cur = get().pinned[home] ?? [];
    const next = cur.includes(device) ? cur.filter((d) => d !== device) : [...cur, device];
    const pinned = { ...get().pinned, [home]: next };
    save("sh.pinned", pinned);
    set({ pinned });
  },
}));

export function applyTheme(theme: Prefs["theme"]) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}
