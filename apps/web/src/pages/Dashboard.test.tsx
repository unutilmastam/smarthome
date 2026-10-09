import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Dashboard } from "./Dashboard";
import { cap, device, mockFetch, ok, renderWithProviders, setMe, v } from "../test/utils";

describe("Dashboard", () => {
  it("renders devices without a render loop", async () => {
    setMe(true);
    const d = device({ switch: cap("control_basic", "low", { on: v(true) }) }, { name: "Chiroq" });
    mockFetch((url) => {
      if (url.endsWith("/homes")) return ok([{ id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null, my_role: "owner" }]);
      if (url.includes("/homes/h1/devices")) return ok([d]);
      return undefined;
    });
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("Chiroq")).toBeInTheDocument();
    expect(screen.getByText("Qurilmani ★ bilan bosh sahifaga qo'shing.")).toBeInTheDocument();
  });
});
