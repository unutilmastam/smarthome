import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Device } from "../api/types";
import { groupPanels } from "../lib/panel";
import { cap, device, mockFetch, ok, renderWithProviders, setMe, unknown, v } from "../test/utils";
import { AddDeviceSheet } from "./AddForms";
import { BreakerPanels } from "./BreakerPanel";

const HOME = { id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null, my_role: "owner" };

function breaker(key: string, name: string, position: number | undefined, state: Record<string, ReturnType<typeof v>>,
  extra: Partial<Device> = {}, cfg: Record<string, unknown> = {}): Device {
  return device({ breaker: cap("control_power", "high", state, { position, ...cfg }) },
    { id: `id-${key}`, key, name, ...extra });
}

const ON = { closed: v(true), tripped: v(false) };
const OFF = { closed: v(false), tripped: v(false) };

describe("electrical panel", () => {
  beforeEach(() => setMe(true));

  it("lines breakers up by their label number, panel by panel", () => {
    const list = [
      breaker("b3", "Konditsioner", 3, ON),
      breaker("b1", "Oshxona", 1, ON, {}, { rating_a: 16, curve: "C" }),
      breaker("b2", "Yotoqxona", 2, OFF),
      breaker("g1", "Garaj", 1, ON, {}, { panel: "Hovli shiti" }),
      breaker("bx", "Raqamsiz", undefined, ON),
    ];
    const panels = groupPanels(list);
    expect(panels.map((p) => p.panel)).toEqual(["", "Hovli shiti"]);
    expect(panels[0].items.map((i) => i.device.key)).toEqual(["b1", "b2", "b3", "bx"]);
    expect(panels[0].items[0].rating).toBe("C16");
  });

  it("shows the reported state only: unknown lever is in the middle and cannot be flipped", async () => {
    mockFetch((url) => (url.endsWith("/homes") ? ok([HOME]) : undefined));
    renderWithProviders(<BreakerPanels role="owner" devices={[
      breaker("b1", "Oshxona", 1, ON),
      breaker("b2", "Yotoqxona", 2, OFF),
      breaker("b3", "Bolalar", 3, { closed: unknown(), tripped: unknown() }),
    ]} />);
    expect(screen.getByText("Asosiy shit")).toBeInTheDocument();
    expect(screen.getByText(/3 ta avtomat · 1 yoqilgan · 1 o.chiq/)).toHaveTextContent("1 ta noma'lum");
    expect(screen.getByRole("switch", { name: "1 — Oshxona" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("switch", { name: "2 — Yotoqxona" })).toHaveAttribute("aria-checked", "false");
    const unk = screen.getByRole("switch", { name: "3 — Bolalar" });
    expect(unk).toHaveAttribute("aria-checked", "mixed");
    expect(unk).toBeDisabled();
    expect(screen.getByTestId("breaker-b3")).toHaveAttribute("data-state", "unknown");
  });

  it("switching off asks for the PIN, then sends breaker.open with it", async () => {
    const calls = mockFetch((url, init) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.endsWith("/commands") && init.method === "POST")
        return ok({ id: "c1", capability: "breaker", action: "open", status: "queued", reason: null });
      if (url.endsWith("/commands/c1")) return ok({ id: "c1", capability: "breaker", action: "open", status: "confirmed", reason: null });
      return undefined;
    });
    renderWithProviders(<BreakerPanels role="owner" devices={[breaker("b1", "Oshxona", 1, ON)]} />);
    await userEvent.click(screen.getByRole("switch", { name: "1 — Oshxona" }));
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
    expect(await screen.findByText(/1 — Oshxona: O'chirish/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("PIN"), "4821");
    await userEvent.click(screen.getByRole("button", { name: "Tasdiqlash" }));
    expect(calls.find((c) => c.method === "POST")!.body)
      .toMatchObject({ capability: "breaker", action: "open", confirm_pin: "4821" });
    expect(await screen.findByText("Tasdiqlandi")).toBeInTheDocument();
  });

  it("a tripped breaker is red, says so, and cannot be switched on from the app", () => {
    mockFetch((url) => (url.endsWith("/homes") ? ok([HOME]) : undefined));
    renderWithProviders(<BreakerPanels role="owner" devices={[breaker("b1", "Oshxona", 1, { closed: v(false), tripped: v(true) })]} />);
    const mod = screen.getByTestId("breaker-b1");
    expect(mod).toHaveAttribute("data-state", "tripped");
    expect(within(mod).getByText("Himoya ishladi")).toBeInTheDocument();
    expect(within(mod).getByRole("switch")).toBeDisabled();
    expect(screen.getByText(/1 ta himoya ishlagan/)).toBeInTheDocument();
  });

  it("family can see the panel but not switch, and duplicate numbers are flagged", () => {
    mockFetch((url) => (url.endsWith("/homes") ? ok([{ ...HOME, my_role: "family" }]) : undefined));
    renderWithProviders(<BreakerPanels role="family" devices={[breaker("b1", "Oshxona", 1, ON), breaker("b2", "Hammom", 1, ON)]} />);
    for (const s of screen.getAllByRole("switch")) expect(s).toBeDisabled();
    expect(screen.getByText(/faqat uy egasi yoki admin/)).toBeInTheDocument();
    expect(screen.getAllByTitle("Bu raqam shitda takrorlangan")).toHaveLength(2);
  });

  it("adding a breaker suggests the next free number and sends the panel config", async () => {
    const calls = mockFetch((_url, init) => (init.method === "POST" ? ok({ id: "new" }) : undefined));
    const existing = [breaker("avtomat_oshxona", "Oshxona", 1, ON), breaker("avtomat_zal", "Zal", 2, ON)];
    renderWithProviders(<AddDeviceSheet open onClose={() => undefined} homeId="h1" rooms={[]} devices={existing} />);
    await userEvent.click(screen.getByRole("button", { name: "Avtomat (shit)" }));
    expect(screen.getByLabelText("Shitdagi raqami")).toHaveValue(3);
    await userEvent.type(screen.getByLabelText("Liniya nomi"), "Oshxona 2");
    expect(screen.getByLabelText(/Kalit/)).toHaveValue("avtomat_oshxona_2");
    await userEvent.selectOptions(screen.getByLabelText("Xarakteristika"), "C");
    await userEvent.selectOptions(screen.getByLabelText("Nominal tok"), "16");
    await userEvent.click(screen.getByLabelText(/Quvvatni ham o'lchaydi/));
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(calls[0].body).toMatchObject({
      name: "Oshxona 2", icon: "breaker",
      capabilities: { breaker: { position: 3, poles: 1, rating_a: 16, curve: "C" }, power_meter: {} },
    });
  });
});
