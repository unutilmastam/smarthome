/* Web Push handler (ADR 0014), imported into the Workbox service worker.
 * Shows exactly what the server sent; "Ko'rdim" acknowledges with the per-notification
 * HMAC token from the payload (the service worker has no access token, ADR 0009). */
/* eslint-env serviceworker */

self.addEventListener("push", (event) => {
  let p = {};
  try { p = event.data ? event.data.json() : {}; } catch (e) { p = { title: event.data && event.data.text() }; }
  const options = {
    body: p.body || "",
    tag: p.id || undefined,
    renotify: !!p.reminder,
    requireInteraction: p.severity === "critical",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    data: { id: p.id, url: p.url || "/notifications", ack: p.ack || null },
    actions: p.ack ? [{ action: "ack", title: "Ko'rdim" }] : [],
  };
  event.waitUntil(self.registration.showNotification(p.title || "SmartHome", options));
});

self.addEventListener("notificationclick", (event) => {
  const d = event.notification.data || {};
  event.notification.close();
  if (event.action === "ack" && d.ack && d.id) {
    event.waitUntil(fetch(`/api/v1/notifications/${d.id}/ack-token`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Client": "web" },
      body: JSON.stringify(d.ack),
    }).catch(() => undefined));
    return;
  }
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if ("focus" in c) { await c.focus(); if ("navigate" in c) await c.navigate(d.url); return; }
    }
    await self.clients.openWindow(d.url);
  })());
});
