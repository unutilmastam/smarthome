import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

interface Creds {
  enabled: boolean; url?: string; username?: string; password?: string;
  client_id?: string; topics?: string[];
}

/**
 * Live updates through the managed broker (ADR 0008), read-only credentials.
 * Disconnects while the app is hidden (free-tier session minutes) and falls back
 * to polling whenever the broker is unavailable.
 */
export function useRealtime(homeId?: string): "realtime" | "polling" {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"realtime" | "polling">("polling");

  useEffect(() => {
    if (!homeId) return;
    let client: { end: (force?: boolean) => void } | null = null;
    let cancelled = false;

    const connect = async () => {
      let creds: Creds;
      try { creds = await api.get<Creds>("/realtime/credentials"); } catch { setMode("polling"); return; }
      if (!creds.enabled || !creds.url || cancelled) { setMode("polling"); return; }
      const mqtt = await import("mqtt");
      if (cancelled) return;
      const c = mqtt.connect(creds.url, {
        username: creds.username, password: creds.password, clientId: creds.client_id,
        reconnectPeriod: 5000, connectTimeout: 8000, clean: true,
      });
      client = c;
      c.on("connect", () => {
        setMode("realtime");
        for (const t of creds.topics ?? []) c.subscribe(t, { qos: 1 });
      });
      c.on("close", () => setMode("polling"));
      c.on("error", () => setMode("polling"));
      c.on("message", (topic: string) => {
        const parts = topic.split("/"); // sh/v1/{home}/dev/{device}/state
        if (parts[3] === "dev" && parts[4]) void qc.invalidateQueries({ queryKey: ["device", parts[4]] });
        void qc.invalidateQueries({ queryKey: ["devices", homeId] });
        if (parts[3] === "hub") void qc.invalidateQueries({ queryKey: ["hubs", homeId] });
      });
    };
    const disconnect = () => { client?.end(true); client = null; setMode("polling"); };
    const onVisibility = () => { if (document.hidden) disconnect(); else if (!client) void connect(); };

    void connect();
    document.addEventListener("visibilitychange", onVisibility);
    return () => { cancelled = true; document.removeEventListener("visibilitychange", onVisibility); disconnect(); };
  }, [homeId, qc]);

  return mode;
}
