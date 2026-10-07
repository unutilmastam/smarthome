import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Energy } from "./Energy";
import { cap, device, mockFetch, ok, renderWithProviders, setMe, unknown, v } from "../test/utils";

const HOME = { id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null, my_role: "owner", tariff_per_kwh: null, currency: "UZS" };
const summary = (period: string, kwh: number | null, cost: number | null, tariff: number | null) =>
  ok({ period, from: "2026-10-01", to: "2026-10-31", timezone: "Asia/Tashkent", tariff_per_kwh: tariff, currency: "UZS",
       total_kwh: kwh, total_cost: cost, devices: kwh === null ? [] : [{ device_id: "d1", key: "m", name: "M", kwh, cost, currency: cost === null ? null : "UZS", days_with_data: 1 }] });

describe("Energy", () => {
  it("never shows 0 when there is no data, and no cost without a tariff", async () => {
    setMe(true);
    const meter = device({ power_meter: cap("view", "low", { voltage: v(229.8, { unit: "V" }), current: unknown(), power: v(410, { unit: "W" }),
      energy: unknown(), power_factor: unknown(), frequency: { value: null, source: "reported", quality: "not_supported", ts: null } }) }, { name: "Hisoblagich" });
    mockFetch((url) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.includes("period=day")) return summary("day", 3.5, null, null);
      if (url.includes("period=month")) return summary("month", null, null, null);
      if (url.includes("/devices?")) return ok([meter]);
      if (url.includes("/telemetry")) return ok([]);
      return undefined;
    });
    renderWithProviders(<Energy />);
    expect(await screen.findByText("3.5 kVt·soat")).toBeInTheDocument();
    expect(screen.getAllByText(/Tarif kiritilmagan/).length).toBeGreaterThan(0);
    expect(screen.getByTestId("energy-month")).toHaveTextContent("Ma'lumot yo'q");
    expect(screen.getByTestId("energy-month")).not.toHaveTextContent("0 kVt");
    expect(await screen.findByText("Hisoblagich")).toBeInTheDocument();
    expect(screen.getByTestId("value-Chastota")).toHaveTextContent("Qo'llab-quvvatlanmaydi");
  });
});
