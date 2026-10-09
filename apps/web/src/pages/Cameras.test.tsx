import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Cameras } from "./Cameras";
import { mockFetch, ok, renderWithProviders, v } from "../test/utils";

const home = (role: string) => ({ id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null, my_role: role, tariff_per_kwh: null, currency: "UZS" });
const CAM = { id: "c1", name: "Darvoza", frigate_name: "gate_cam", availability: { status: "online" },
  status: { stream_available: v(true), recording: v(true), disk_usage_pct: v(91, { unit: "%" }) } };

describe("Cameras", () => {
  it("shows links to the hub only, never a video element", async () => {
    mockFetch((url) => {
      if (url.endsWith("/homes")) return ok([home("owner")]);
      if (url.endsWith("/homes/h1/cameras")) return ok([CAM]);
      if (url.endsWith("/cameras/c1/access")) return ok({ links: { tailscale: "https://hub.ts.net:8971/" }, archive_allowed: true });
      return undefined;
    });
    const { container } = renderWithProviders(<Cameras />);
    expect(await screen.findByText("Darvoza")).toBeInTheDocument();
    expect(screen.getByText(/Disk 91% to'lgan/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Jonli ko'rish" }));
    const link = await screen.findByRole("link", { name: /Tailscale orqali/ });
    expect(link).toHaveAttribute("href", "https://hub.ts.net:8971/");
    expect(container.querySelector("video, img")).toBeNull();
  });

  it("family has no live button", async () => {
    mockFetch((url) => (url.endsWith("/homes") ? ok([home("family")]) : url.endsWith("/cameras") ? ok([CAM]) : undefined));
    renderWithProviders(<Cameras />);
    expect(await screen.findByText("Sizda jonli ko'rish ruxsati yo'q.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Jonli ko'rish" })).not.toBeInTheDocument();
  });
});
