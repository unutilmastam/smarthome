import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AutomationEditor } from "./AutomationEditor";
import { cap, device, err, mockFetch, ok, renderWithProviders, unknown } from "../test/utils";
import type { Home } from "../api/types";
import i18n from "../i18n";
import { summary } from "../lib/automation";

const HOME: Home = { id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null,
  my_role: "owner", tariff_per_kwh: null, currency: "UZS" };
const radar = device({ motion: cap("view", "low", { detected: unknown() }) }, { id: "r", key: "garden_radar", name: "Radar" });
const light = device({ switch: cap("control_basic", "low", { on: unknown() }) }, { id: "l", key: "garden_lights", name: "Bog' chiroqlari" });
const gate = device({ cover: cap("control_access", "high", { state: unknown(), position: unknown() }) }, { id: "g", key: "front_gate", name: "Darvoza" });
const DEVICES = [radar, light, gate];

describe("automation editor", () => {
  it("builds the contract JSON: motion -> light on with auto off", async () => {
    const calls = mockFetch((url, init) => (url.endsWith("/homes/h1/automations") && init.method === "POST" ? ok({ id: "a1" }) : undefined));
    renderWithProviders(<AutomationEditor open onClose={() => undefined} home={HOME} devices={DEVICES} />);
    await userEvent.type(screen.getByLabelText("Nomi"), "Bog' chirog'i");
    await userEvent.click(screen.getAllByRole("button", { name: /Qurilma holati/ })[0]);   // "Qachon?" block
    await userEvent.click(screen.getByRole("button", { name: /Buyruq/ }));
    const auto = screen.getByLabelText(/Avtomatik o'chirish/);
    await userEvent.clear(auto);
    await userEvent.type(auto, "5");
    await userEvent.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(calls[0].body).toMatchObject({
      name: "Bog' chirog'i",
      definition: {
        triggers: [{ type: "state", device: "garden_radar", capability: "motion", attribute: "detected", to: true }],
        actions: [{ type: "command", device: "garden_lights", capability: "switch", action: "turn_on", auto_off_after_s: 300 }],
      },
    });
  });

  it("never offers high-risk devices (gate) as automation actions", async () => {
    mockFetch(() => undefined);
    renderWithProviders(<AutomationEditor open onClose={() => undefined} home={HOME} devices={DEVICES} />);
    await userEvent.click(screen.getByRole("button", { name: /Buyruq/ }));
    const selects = screen.getAllByLabelText("Qurilma");
    const select = selects[selects.length - 1];
    const names = within(select).getAllByRole("option").map((o) => o.textContent);
    expect(names).toContain("Bog' chiroqlari");
    expect(names).not.toContain("Darvoza");
    expect(screen.getByText(/faqat odam PIN bilan/)).toBeInTheDocument();
  });

  it("sun rules need home coordinates; backend errors are shown in full", async () => {
    mockFetch(() => err(422, "VALIDATION_ERROR"));
    renderWithProviders(<AutomationEditor open onClose={() => undefined} home={HOME} devices={DEVICES} />);
    await userEvent.type(screen.getByLabelText("Nomi"), "Tun");
    await userEvent.click(screen.getByRole("button", { name: /^Quyosh$/ }));
    await userEvent.click(screen.getByRole("button", { name: /Xabar/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("Uy joylashuvi");
    expect(screen.getByRole("button", { name: "Saqlash" })).toBeDisabled();
  });

  it("summarises a rule in words", () => {
    const t = i18n.t.bind(i18n) as (k: string, o?: Record<string, unknown>) => string;
    const s = summary(t, {
      triggers: [{ type: "state", device: "garden_radar", capability: "motion", attribute: "detected", to: true }],
      conditions: [{ type: "sun", is: "night" }],
      actions: [{ type: "command", device: "garden_lights", capability: "switch", action: "turn_on" }],
    }, DEVICES);
    expect(s).toBe("Radar: Harakat bor (Kechasi) → Bog' chiroqlari: Yoqish");
  });
});
