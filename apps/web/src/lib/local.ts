/**
 * Local mode (ARCHITECTURE 0.4). An https PWA cannot probe http://hub.local (mixed
 * content), so local mode is detected only when the app itself is served by the hub.
 * The hub's local-api is built in a later phase.
 */
export function isLocalHub(hostname = window.location.hostname): boolean {
  return hostname === "hub.local" || hostname.endsWith(".local");
}
