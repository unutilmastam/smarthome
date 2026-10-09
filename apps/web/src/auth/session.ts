import { create } from "zustand";
import { api, ApiError, onLoggedOut, refreshSession, setAccessToken } from "../api/client";

export interface Me { id: string; email: string; name: string; has_pin: boolean }

interface SessionState {
  status: "loading" | "anonymous" | "authenticated";
  me: Me | null;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reloadMe: () => Promise<void>;
}

export const useSession = create<SessionState>((set) => ({
  status: "loading",
  me: null,
  bootstrap: async () => {
    if (await refreshSession()) {
      try {
        set({ me: await api.get<Me>("/auth/me"), status: "authenticated" });
        return;
      } catch { /* fall through */ }
    }
    set({ status: "anonymous", me: null });
  },
  login: async (email, password) => {
    const data = await api.post<{ access_token: string; user: Me }>("/auth/login", { email, password });
    setAccessToken(data.access_token);
    set({ me: data.user, status: "authenticated" });
  },
  logout: async () => {
    try { await api.post("/auth/logout"); } catch (e) { if (!(e instanceof ApiError)) throw e; }
    setAccessToken(null);
    set({ status: "anonymous", me: null });
  },
  reloadMe: async () => { set({ me: await api.get<Me>("/auth/me") }); },
}));

onLoggedOut(() => {
  setAccessToken(null);
  useSession.setState({ status: "anonymous", me: null });
});
