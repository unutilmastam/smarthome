import { describe, expect, it, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeviceControls } from "./DeviceControls";
import { EventList } from "./EventFeed";
import { IrrigationStop } from "./IrrigationStop";
import { cap, device, mockFetch, ok, renderWithProviders, setMe, unknown, v } from "../test/utils";
import { formatValue } from "../lib/status";
import i18n from "../i18n";
import type { HomeEvent } from "../api/types";

beforeEach(() => setMe(true));

const HOME = { id: "h1", name: "Uy", my_role: "owner", timezone: "Asia/Tashkent" };
const homes = (url: string) => (url.endsWith("/homes") ? ok([HOME]) : undefined);

describe("alarm control", () => {
  const alarm = (state: unknown, zone = "") => device(
    { alarm: cap("control_access", "high", { state: state === null ? unknown() : v(state), alert_zone: v(zone) }) },
    { key: "security", adapter: "hub" });

  it("arming asks for the PIN first (high risk) and sends arm_away", async () => {
    const calls = mockFetch((url, init) => homes(url) ?? (url.endsWith("/commands") && init.method === "POST"
      ? ok({ id: "c1", capability: "alarm", action: "arm_away", status: "queued", reason: null }) : undefined));
    renderWithProviders(<DeviceControls device={alarm("disarmed")} role="owner" />);
    expect(screen.getByTestId("alarm-state")).toHaveTextContent("Qo'riqlanmayapti");
    await userEvent.click(screen.getByRole("button", { name: /Uydan chiqyapman/ }));
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
    await userEvent.type(await screen.findByLabelText("PIN"), "4821");
    await userEvent.click(screen.getByRole("button", { name: "Tasdiqlash" }));
    expect(calls.find((c) => c.method === "POST")!.body).toMatchObject({ capability: "alarm", action: "arm_away", confirm_pin: "4821" });
  });

  it("shows the triggered zone and an unknown state honestly", () => {
    mockFetch(homes);
    const { unmount } = renderWithProviders(<DeviceControls device={alarm("triggered", "front_door")} role="owner" />);
    expect(screen.getByTestId("alarm-state")).toHaveAttribute("data-state", "triggered");
    expect(screen.getByTestId("alarm-state")).toHaveTextContent("Zona: front_door");
    unmount();
    renderWithProviders(<DeviceControls device={alarm(null)} role="owner" />);
    expect(screen.getByTestId("alarm-state")).toHaveAttribute("data-state", "unknown");
    expect(screen.getByTestId("alarm-state")).not.toHaveTextContent("Qo'riqlanmoqda");
  });

  it("guests cannot arm or disarm", () => {
    mockFetch(homes);
    renderWithProviders(<DeviceControls device={alarm("armed_away")} role="guest" />);
    expect(screen.getByRole("button", { name: /Qo'riqlashni o'chirish/ })).toBeDisabled();
  });
});

describe("feedback attributes", () => {
  it("speaks about the attribute, not generic on/off", () => {
    const t = i18n.t.bind(i18n) as (k: string, o?: Record<string, unknown>) => string;
    expect(formatValue(v(true), t, "obstructed")).toBe("To'silgan!");
    expect(formatValue(v(false), t, "running")).toBe("Ishlamayapti");
    expect(formatValue(v(true), t)).toBe("Yoqilgan");
    expect(formatValue(unknown(), t, "running")).toBe("—");
  });
});

describe("irrigation emergency stop", () => {
  const valve = (id: string, open: unknown) => device({ valve: cap("control_basic", "medium",
    { open: open === null ? unknown() : v(open), flow: v(10, { unit: "L/min" }), remaining_s: v(60) }) }, { id, name: id });

  it("only appears for valves that REPORT open and closes each of them", async () => {
    const calls = mockFetch((url, init) => homes(url) ?? (url.endsWith("/commands") && init.method === "POST"
      ? ok({ id: "x", status: "queued" }) : undefined));
    renderWithProviders(<IrrigationStop devices={[valve("a", true), valve("b", false), valve("c", null)]} />);
    const btn = await screen.findByRole("button", { name: /Hammasini to'xtatish/ });
    await userEvent.click(btn);
    const posts = calls.filter((c) => c.method === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0].body).toMatchObject({ device_id: "a", capability: "valve", action: "close" });
  });

  it("is hidden when nothing runs", () => {
    mockFetch(homes);
    renderWithProviders(<IrrigationStop devices={[valve("b", false)]} />);
    expect(screen.queryByTestId("irrigation-stop")).toBeNull();
  });
});

describe("event feed", () => {
  it("renders contract events with severity and data", () => {
    mockFetch(homes);
    const ev = (type: string, severity: HomeEvent["severity"], data = {}): HomeEvent => ({
      id: type, ts: "2026-10-07T18:00:00Z", type, severity, device_id: "d1", device_key: "front_gate",
      device_name: "Darvoza", data });
    renderWithProviders(<EventList events={[ev("cover.left_open", "warning", { open_s: 900 }),
      ev("alarm.triggered", "critical", { zone: "front_door" })]} />);
    expect(screen.getByTestId("event-cover.left_open")).toHaveTextContent("15 daqiqadan beri ochiq qoldi");
    expect(screen.getByTestId("event-alarm.triggered")).toHaveTextContent("SIGNAL: front_door");
    expect(screen.getByTestId("event-alarm.triggered")).toHaveClass("sev-critical");
  });
});
