import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HubStatus } from "./HubStatus";
import { mockFetch, ok, renderWithProviders } from "../test/utils";

const HOME = { id: "h1", name: "Uy", timezone: "Asia/Tashkent", latitude: null, longitude: null, my_role: "owner" };

describe("HubStatus", () => {
  it("creates a hub and shows the secrets once", async () => {
    let hubs: unknown[] = [];
    mockFetch((url, init) => {
      if (url.endsWith("/homes")) return ok([HOME]);
      if (url.endsWith("/homes/h1/hubs") && init.method === "POST") {
        hubs = [{ id: "x", name: "Asosiy hub", status: "active", online: false, last_seen: null, version: null }];
        return ok({ ...hubs[0] as object, hub_token: "hub_secret", signing_key_hex: "ab".repeat(32) });
      }
      if (url.endsWith("/homes/h1/hubs")) return ok(hubs);
      return undefined;
    });
    renderWithProviders(<HubStatus />);
    await userEvent.click(await screen.findByRole("button", { name: "Hub qo'shish" }));
    expect(await screen.findByDisplayValue("hub_secret")).toBeInTheDocument();
    expect(screen.getByDisplayValue("ab".repeat(32))).toBeInTheDocument();
    // An active hub exists now: no second "add" form.
    expect(screen.queryByRole("button", { name: "Hub qo'shish" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Yopish" }));
    expect(screen.queryByDisplayValue("hub_secret")).not.toBeInTheDocument();
  });

  it("family members cannot add hubs", async () => {
    mockFetch((url) => (url.endsWith("/homes") ? ok([{ ...HOME, my_role: "family" }]) : url.endsWith("/hubs") ? ok([]) : undefined));
    renderWithProviders(<HubStatus />);
    expect(await screen.findByText("Hub ulanmagan")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hub qo'shish" })).not.toBeInTheDocument();
  });
});
