import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Notifications } from "../pages/Notifications";
import { NotificationSettings } from "./NotificationSettings";
import { mockFetch, ok, renderWithProviders } from "../test/utils";

const HOME = { id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null, my_role: "owner" };
const DOOR = { id: "d2", key: "front_door", name: "Old eshik", capabilities: {}, availability: { status: "online", ts: null } };

const note = (over: Record<string, unknown> = {}) => ({
  id: "n1", ts: "2026-10-08T10:00:00Z", created_at: "2026-10-08T10:00:01Z", severity: "critical", source: "event",
  kind: "alarm.triggered", title: "SIGNAL: Old eshik", body: "📍 Signalizatsiya",
  data: { zone: "front_door", device_key: "security" }, needs_ack: true, acked_at: null, acked_by: null, acked_by_name: null, ...over,
});

const channels = (over: Record<string, unknown> = {}) => ({
  telegram: { available: true, links: [] },
  push: { available: true, public_key: "BP4z", subscriptions: [] }, ...over,
});

describe("Notifications page", () => {
  it("shows the event in words with the zone's device name and acks it", async () => {
    let acked = false;
    const calls = mockFetch((url, init) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.includes("/homes/h1/devices")) return ok([DOOR]);
      if (url.includes("/homes/h1/notifications")) {
        const n = acked ? note({ acked_at: "2026-10-08T10:01:00Z", acked_by_name: "Owner" }) : note();
        return { body: { data: [n], error: null, meta: { unacked: acked ? 0 : 1 } } };
      }
      if (url.endsWith("/notifications/n1/ack") && init.method === "POST") { acked = true; return ok(note()); }
      return undefined;
    });
    renderWithProviders(<Notifications />);
    expect(await screen.findByText("SIGNAL: Old eshik")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tasdiqlanmagan \(1\)/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ko'rdim" }));
    expect(await screen.findByText(/Ko'rdi: Owner/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ko'rdim" })).not.toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST" && c.url.endsWith("/notifications/n1/ack"))).toBe(true);
  });

  it("viewers see notifications but have no ack button; system kinds are translated", async () => {
    mockFetch((url) => {
      if (url.endsWith("/homes")) return ok([{ ...HOME, my_role: "viewer" }]);
      if (url.includes("/devices")) return ok([]);
      if (url.includes("/notifications")) return { body: { data: [note({
        id: "n2", source: "hub", kind: "hub.offline", title: "x", body: "🖥 hub", data: { minutes: 3 } })], error: null, meta: { unacked: 1 } } };
      return undefined;
    });
    renderWithProviders(<Notifications />);
    expect(await screen.findByText("Hub aloqasiz: 3 daqiqadan beri javob yo'q")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ko'rdim" })).not.toBeInTheDocument();
  });
});

describe("NotificationSettings", () => {
  it("links Telegram with a one-time code and a t.me link", async () => {
    mockFetch((url, init) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.endsWith("/notification-prefs")) return ok({ notify_min_severity: "warning", receives: true });
      if (url.endsWith("/notifications/settings")) return ok(channels());
      if (url.endsWith("/notifications/telegram/link") && init.method === "POST")
        return ok({ code: "ABCD2345", expires_at: "2026-10-08T10:10:00Z", bot_username: "uy_bot", url: "https://t.me/uy_bot?start=ABCD2345" });
      return undefined;
    });
    renderWithProviders(<NotificationSettings />);
    await userEvent.click(await screen.findByRole("button", { name: "Telegram'ni bog'lash" }));
    expect(await screen.findByText("ABCD2345")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Telegram'da ochish/ })).toHaveAttribute("href", "https://t.me/uy_bot?start=ABCD2345");
  });

  it("says plainly when the server has no channels and when nothing is linked for the test", async () => {
    mockFetch((url, init) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.endsWith("/notification-prefs")) return ok({ notify_min_severity: "warning", receives: true });
      if (url.endsWith("/notifications/settings"))
        return ok(channels({ telegram: { available: false, links: [] }, push: { available: false, public_key: null, subscriptions: [] } }));
      if (url.endsWith("/notifications:test") && init.method === "POST") return ok({ id: "t", deliveries: [] });
      return undefined;
    });
    renderWithProviders(<NotificationSettings />);
    await waitFor(() => expect(screen.getAllByText("Serverda hali sozlanmagan.")).toHaveLength(2));
    await userEvent.click(screen.getByRole("button", { name: /Sinov xabarini yuborish/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Hech qaysi kanal ulanmagan");
  });

  it("changes the level and reports real test results per channel", async () => {
    const calls = mockFetch((url, init) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.endsWith("/notification-prefs")) return ok({ notify_min_severity: "warning", receives: true });
      if (url.endsWith("/notifications/settings"))
        return ok(channels({ telegram: { available: true, links: [{ id: "l1", username: "ali", created_at: "2026-10-08T09:00:00Z" }] } }));
      if (url.endsWith("/notifications:test") && init.method === "POST")
        return ok({ id: "t", deliveries: [{ channel: "telegram", status: "sent" }, { channel: "push", status: "pending" }] });
      return undefined;
    });
    renderWithProviders(<NotificationSettings />);
    expect(await screen.findByText(/Bog'langan: @ali/)).toBeInTheDocument();
    await userEvent.selectOptions(await screen.findByLabelText("Qaysi xabarlar telefonga kelsin"), "critical");
    await waitFor(() => expect(calls.some((c) => c.method === "PUT" && (c.body as { notify_min_severity: string }).notify_min_severity === "critical")).toBe(true));
    await userEvent.click(screen.getByRole("button", { name: /Sinov xabarini yuborish/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Telegram: yuborildi · Push (shu qurilma): yuborilmadi, qayta urinadi");
  });
});
