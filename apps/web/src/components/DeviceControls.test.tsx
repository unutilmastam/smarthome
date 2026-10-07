import { describe, expect, it, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeviceControls } from "./DeviceControls";
import { cap, device, err, mockFetch, ok, renderWithProviders, setMe, unknown, v } from "../test/utils";

const light = device({ switch: cap("control_basic", "low", { on: v(false) }) });

beforeEach(() => setMe(true));

describe("switch", () => {
  it("follows the real lifecycle and is not optimistic", async () => {
    let polls = 0;
    const calls = mockFetch((url, init) => {
      if (url.endsWith("/commands") && init.method === "POST") return ok({ id: "c1", capability: "switch", action: "turn_on", status: "queued", reason: null });
      if (url.endsWith("/commands/c1")) {
        polls += 1;
        return ok({ id: "c1", capability: "switch", action: "turn_on", status: polls < 2 ? "acked" : "confirmed", reason: null });
      }
      return undefined;
    });
    renderWithProviders(<DeviceControls device={light} role="family" />);
    await userEvent.click(screen.getByRole("button", { name: "Yoqish" }));
    const post = calls.find((c) => c.method === "POST")!;
    expect(post.body).toMatchObject({ device_id: "d1", capability: "switch", action: "turn_on", params: {} });
    expect((post.body as { idempotency_key: string }).idempotency_key.length).toBeGreaterThan(8);
    // Displayed device value is still the reported one (Off) while pending.
    expect(screen.getByTestId("value-Holat")).toHaveTextContent("O'chirilgan");
    await waitFor(() => expect(screen.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed"), { timeout: 3000 });
  });

  it("shows HUB_UNREACHABLE clearly", async () => {
    mockFetch((url) => (url.endsWith("/commands") ? err(503, "HUB_UNREACHABLE") : undefined));
    renderWithProviders(<DeviceControls device={light} role="owner" />);
    await userEvent.click(screen.getByRole("button", { name: "Yoqish" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Hub bilan aloqa yo'q");
  });

  it("viewer cannot control", () => {
    mockFetch(() => undefined);
    renderWithProviders(<DeviceControls device={light} role="viewer" />);
    expect(screen.getByRole("button", { name: "Yoqish" })).toBeDisabled();
    expect(screen.getByText("Sizda boshqarish ruxsati yo'q")).toBeInTheDocument();
  });

  it("disables controls when the hub is offline", () => {
    mockFetch(() => undefined);
    renderWithProviders(<DeviceControls device={{ ...light, hub_online: false }} role="owner" />);
    expect(screen.getByRole("button", { name: "Yoqish" })).toBeDisabled();
  });

  it("unknown value is shown as unknown, never as Off", () => {
    mockFetch(() => undefined);
    const d = device({ switch: cap("control_basic", "low", { on: unknown() }) });
    renderWithProviders(<DeviceControls device={d} role="owner" />);
    const row = screen.getByTestId("value-Holat");
    expect(row).toHaveTextContent("—");
    expect(row).toHaveTextContent("Noma'lum");
    expect(row).not.toHaveTextContent("O'chirilgan");
  });
});

describe("gate (high risk)", () => {
  const gate = device({ cover: cap("control_access", "high", { position: v(0, { unit: "%" }), state: v("closed") }) });

  it("asks for the PIN and sends confirm_pin", async () => {
    const calls = mockFetch((url, init) => (url.endsWith("/commands") && init.method === "POST"
      ? ok({ id: "c2", capability: "cover", action: "open", status: "queued", reason: null })
      : url.endsWith("/commands/c2") ? ok({ id: "c2", capability: "cover", action: "open", status: "confirmed", reason: null }) : undefined));
    renderWithProviders(<DeviceControls device={gate} role="family" />);
    await userEvent.click(screen.getByRole("button", { name: "Ochish" }));
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
    const input = await screen.findByLabelText("PIN");
    await userEvent.type(input, "48a21");
    await userEvent.click(screen.getByRole("button", { name: "Tasdiqlash" }));
    const post = calls.find((c) => c.method === "POST")!;
    expect(post.body).toMatchObject({ capability: "cover", action: "open", confirm_pin: "4821" });
  });

  it("cancel sends nothing", async () => {
    const calls = mockFetch(() => undefined);
    renderWithProviders(<DeviceControls device={gate} role="owner" />);
    await userEvent.click(screen.getByRole("button", { name: "Ochish" }));
    await userEvent.click(await screen.findByRole("button", { name: "Bekor qilish" }));
    expect(calls).toHaveLength(0);
  });

  it("without a PIN set, tells the user to set one", async () => {
    setMe(false);
    mockFetch(() => undefined);
    renderWithProviders(<DeviceControls device={gate} role="owner" />);
    await userEvent.click(screen.getByRole("button", { name: "Ochish" }));
    expect(screen.getByText("Avval Sozlamalarda PIN o'rnating.")).toBeInTheDocument();
  });
});

describe("valve", () => {
  const valve = device({ valve: cap("control_basic", "medium", { open: v(false), flow: unknown(), remaining_s: unknown() }, { max_runtime_s: 1200 }) });

  it("requires a duration within the device max_runtime", async () => {
    const calls = mockFetch((url, init) => (url.endsWith("/commands") && init.method === "POST"
      ? ok({ id: "c3", capability: "valve", action: "open", status: "queued", reason: null }) : undefined));
    renderWithProviders(<DeviceControls device={valve} role="family" />);
    const open = screen.getByRole("button", { name: "Ochish" });
    expect(open).toBeDisabled();
    const input = screen.getByLabelText(/Davomiylik/);
    await userEvent.type(input, "30");
    expect(open).toBeDisabled(); // 30 min > 20 min max
    await userEvent.clear(input);
    await userEvent.type(input, "15");
    expect(open).toBeEnabled();
    await userEvent.click(open);
    expect(calls.find((c) => c.method === "POST")!.body).toMatchObject({ action: "open", params: { duration_s: 900 } });
  });
});

describe("IR climate", () => {
  it("labels assumed state", () => {
    mockFetch(() => undefined);
    const ac = device({ climate: cap("control_basic", "low", {
      power: v(true, { source: "assumed" }), current_temp: v(26.5, { unit: "°C" }), target_temp: unknown(),
      mode: unknown(), fan: unknown(), humidity: unknown() }) });
    renderWithProviders(<DeviceControls device={ac} role="owner" />);
    expect(screen.getByTestId("value-Quvvat")).toHaveTextContent("Taxminiy");
    expect(screen.getByText(/IR qurilma/)).toBeInTheDocument();
  });
});

describe("command tracking race", () => {
  it("a late response for an older command never overwrites the newer one", async () => {
    setMe(true);
    let releaseOld: (() => void) | null = null;
    let c1Polls = 0;
    let posts = 0;
    globalThis.fetch = (async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const url = String(input);
      const json = (data: unknown) => new Response(JSON.stringify({ data, error: null, meta: {} }), { status: 200 });
      if (url.endsWith("/commands") && init.method === "POST") {
        posts += 1;
        return json({ id: `c${posts}`, capability: "switch", action: posts === 1 ? "turn_on" : "turn_off", status: "queued", reason: null });
      }
      if (url.endsWith("/commands/c1")) {
        c1Polls += 1;
        if (c1Polls === 1) return json({ id: "c1", capability: "switch", action: "turn_on", status: "acked", reason: null });
        await new Promise<void>((r) => { releaseOld = r; });   // this poll is slow
        return json({ id: "c1", capability: "switch", action: "turn_on", status: "timeout", reason: "no_feedback" });
      }
      if (url.endsWith("/commands/c2")) return json({ id: "c2", capability: "switch", action: "turn_off", status: "confirmed", reason: null });
      return new Response("{}", { status: 404 });
    }) as typeof fetch;
    const d = device({ switch: cap("control_basic", "low", { on: v(false) }) });
    renderWithProviders(<DeviceControls device={d} role="owner" />);
    await userEvent.click(screen.getByRole("button", { name: "Yoqish" }));
    // c1 is "acked" (not busy) and its next poll is hanging: the user sends c2.
    await waitFor(() => expect(releaseOld).not.toBeNull(), { timeout: 3000 });
    await userEvent.click(screen.getByRole("button", { name: "O'chirish" }));
    await waitFor(() => expect(screen.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed"), { timeout: 3000 });
    releaseOld!();
    await new Promise((r) => setTimeout(r, 1200));
    expect(screen.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed");
  }, 10_000);
});
