import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { Command, CommandStatus } from "../api/types";
import { hasFeedback } from "./contracts";
import { TERMINAL } from "./status";

export interface Tracked {
  id?: string;
  capability: string;
  action: string;
  status: CommandStatus | "sending" | "error";
  reason?: string | null;
  error?: ApiError;
}

const POLL_MS = 500;
const MAX_TRACK_MS = 60_000;

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Sends a command and follows its REAL lifecycle (queued → sent → acked → confirmed).
 * Never optimistic: the displayed device value only changes when the device reports it.
 */
export function useCommand(deviceId: string) {
  const qc = useQueryClient();
  const [tracked, setTracked] = useState<Tracked | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const follow = useCallback((cmd: Command, started: number) => {
    const done = TERMINAL.includes(cmd.status) ||
      (cmd.status === "acked" && !hasFeedback(cmd.capability)) ||
      Date.now() - started > MAX_TRACK_MS;
    setTracked({ id: cmd.id, capability: cmd.capability, action: cmd.action, status: cmd.status, reason: cmd.reason });
    void qc.invalidateQueries({ queryKey: ["device", deviceId] });
    if (done) {
      void qc.invalidateQueries({ queryKey: ["devices"] });
      void qc.invalidateQueries({ queryKey: ["commands", deviceId] });
      return;
    }
    timer.current = setTimeout(async () => {
      try { follow(await api.get<Command>(`/commands/${cmd.id}`), started); }
      catch { timer.current = setTimeout(() => follow(cmd, started), POLL_MS * 2); }
    }, POLL_MS);
  }, [deviceId, qc]);

  const send = useCallback(async (capability: string, action: string,
    params: Record<string, unknown> = {}, confirmPin?: string) => {
    if (timer.current) clearTimeout(timer.current);
    setTracked({ capability, action, status: "sending" });
    try {
      const body: Record<string, unknown> = {
        device_id: deviceId, capability, action, params, idempotency_key: newKey(),
      };
      if (confirmPin) body.confirm_pin = confirmPin;
      const cmd = await api.post<Command>("/commands", body);
      follow(cmd, Date.now());
      return cmd;
    } catch (e) {
      const err = e instanceof ApiError ? e : new ApiError(0, "NETWORK", String(e));
      setTracked({ capability, action, status: "error", error: err });
      throw err;
    }
  }, [deviceId, follow]);

  const busy = !!tracked && ["sending", "queued", "sent"].includes(tracked.status);
  return { send, tracked, busy };
}
