import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddDeviceForm } from "./AddForms";
import { err, mockFetch, ok, renderWithProviders } from "../test/utils";

describe("AddDeviceForm", () => {
  it("creates an ESPHome light with the switch capability", async () => {
    const calls = mockFetch((url, init) => (url.endsWith("/homes/h1/devices") && init.method === "POST" ? ok({ id: "d" }) : undefined));
    renderWithProviders(<AddDeviceForm homeId="h1" rooms={[]} />);
    await userEvent.type(screen.getByLabelText(/Kalit/), "garden_lights");
    await userEvent.type(screen.getByLabelText("Nomi"), "Bog' chiroqlari");
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(calls[0].body).toEqual({ key: "garden_lights", name: "Bog' chiroqlari", adapter: "esphome", protocol: "mqtt", capabilities: { switch: {} } });
    expect(await screen.findByText("Qurilma qo'shildi")).toBeInTheDocument();
  });

  it("a valve requires max_runtime_s", async () => {
    const calls = mockFetch(() => ok({ id: "d" }));
    renderWithProviders(<AddDeviceForm homeId="h1" rooms={[]} />);
    await userEvent.click(screen.getByLabelText("Yoqish/o'chirish"));
    await userEvent.click(screen.getByLabelText("Sug'orish klapani"));
    await userEvent.type(screen.getByLabelText(/Kalit/), "garden_valve");
    await userEvent.type(screen.getByLabelText("Nomi"), "Klapan");
    const rt = screen.getByLabelText(/Maksimal ishlash vaqti/);
    expect(rt).toBeRequired();
    await userEvent.type(rt, "900");
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(calls[0].body).toMatchObject({ capabilities: { valve: { max_runtime_s: 900 } } });
  });

  it("shows backend validation details", async () => {
    mockFetch(() => err(409, "CONFLICT"));
    renderWithProviders(<AddDeviceForm homeId="h1" rooms={[]} />);
    await userEvent.type(screen.getByLabelText(/Kalit/), "dup_key");
    await userEvent.type(screen.getByLabelText("Nomi"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
