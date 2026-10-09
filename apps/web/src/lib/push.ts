/** Web Push in the browser (ADR 0014). Never claims "on" unless the browser really subscribed. */
import { api } from "../api/client";

export type PushSupport = "ok" | "ios_install" | "unsupported";

export function isIOS(): boolean {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && (navigator.maxTouchPoints ?? 0) > 1);
}

export function isStandalone(): boolean {
  return window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
}

/** iOS/iPadOS only allow push for a PWA added to the Home Screen (16.4+). */
export function pushSupport(): PushSupport {
  const apis = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  if (isIOS() && !isStandalone()) return "ios_install";
  return apis ? "ok" : "unsupported";
}

function keyBytes(b64u: string): Uint8Array {
  const pad = "=".repeat((4 - (b64u.length % 4)) % 4);
  const raw = atob((b64u + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function registration(): Promise<ServiceWorkerRegistration> {
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) throw new Error("no_service_worker");
  return navigator.serviceWorker.ready;
}

export async function currentEndpoint(): Promise<string | null> {
  if (pushSupport() !== "ok") return null;
  try {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = await reg?.pushManager.getSubscription();
    return sub?.endpoint ?? null;
  } catch { return null; }
}

/** Ask permission, subscribe this browser and register it with the server. */
export async function enablePush(publicKey: string): Promise<"ok" | "denied"> {
  const perm = await Notification.requestPermission();
  if (perm !== "granted") return "denied";
  const reg = await registration();
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(publicKey) as BufferSource });
  }
  await api.post("/notifications/push/subscribe", { ...sub.toJSON(), user_agent: navigator.userAgent.slice(0, 200) });
  return "ok";
}

export async function disablePush(): Promise<void> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (!sub) return;
  await api.post("/notifications/push/unsubscribe", { endpoint: sub.endpoint });
  await sub.unsubscribe();
}
