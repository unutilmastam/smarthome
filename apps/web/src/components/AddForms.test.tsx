import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddDeviceSheet, RoomSheet } from "./AddForms";
import { err, mockFetch, ok, renderWithProviders } from "../test/utils";
import type { Room } from "../api/types";

const rooms: Room[] = [{ id: "r1", home_id: "h1", name: "Hovli", type: "outdoor", floor_id: null, icon: "plant" }];

describe("AddDeviceSheet", () => {
  it("light type: picks the switch capability, auto key, chosen room and icon", async () => {
    const calls = mockFetch((url, init) => (url.endsWith("/homes/h1/devices") && init.method === "POST" ? ok({ id: "d9" }) : undefined));
    const onClose = vi.fn();
    renderWithProviders(<AddDeviceSheet open onClose={onClose} homeId="h1" rooms={rooms} devices={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Chiroq" }));
    const name = screen.getByLabelText("Nomi");
    await userEvent.clear(name);
    await userEvent.type(name, "Bog' chiroqlari");
    expect(screen.getByLabelText(/Kalit/)).toHaveValue("bog_chiroqlari");
    await userEvent.click(screen.getByRole("radio", { name: /Hovli/ }));
    await userEvent.click(screen.getByRole("radio", { name: "Qandil" }));
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(calls[0].body).toEqual({
      key: "bog_chiroqlari", name: "Bog' chiroqlari", adapter: "esphome", protocol: "mqtt",
      capabilities: { switch: {} }, icon: "ceiling", room_id: "r1",
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("the key can be typed by hand (must match firmware) and avoids taken keys", async () => {
    mockFetch(() => undefined);
    const existing = [{ key: "chiroq" }] as never;
    renderWithProviders(<AddDeviceSheet open onClose={() => undefined} homeId="h1" rooms={[]} devices={existing} />);
    await userEvent.click(screen.getByRole("button", { name: "Chiroq" }));
    const key = screen.getByLabelText(/Kalit/);
    expect(key).toHaveValue("chiroq_2");
    await userEvent.clear(key);
    await userEvent.type(key, "Bad Key");
    expect(screen.getByRole("button", { name: "Qo'shish" })).toBeDisabled();
  });

  it("irrigation valve requires max_runtime_s", async () => {
    const calls = mockFetch(() => ok({ id: "d" }));
    renderWithProviders(<AddDeviceSheet open onClose={() => undefined} homeId="h1" rooms={[]} devices={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Sug'orish klapani" }));
    const add = screen.getByRole("button", { name: "Qo'shish" });
    expect(add).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Maksimal ishlash vaqti/), "900");
    await userEvent.click(add);
    expect(calls[0].body).toMatchObject({ capabilities: { valve: { max_runtime_s: 900 } }, icon: "sprinkler" });
  });

  it("shows backend errors", async () => {
    mockFetch(() => err(409, "CONFLICT"));
    renderWithProviders(<AddDeviceSheet open onClose={() => undefined} homeId="h1" rooms={[]} devices={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Rozetka" }));
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

describe("RoomSheet", () => {
  it("creates a section with an icon", async () => {
    const calls = mockFetch((url, init) => (url.endsWith("/homes/h1/rooms") && init.method === "POST" ? ok({ id: "r2" }) : undefined));
    renderWithProviders(<RoomSheet open onClose={() => undefined} homeId="h1" />);
    await userEvent.type(screen.getByLabelText("Bo'lim nomi"), "Oshxona");
    await userEvent.click(screen.getByRole("radio", { name: "Oshxona" }));
    await userEvent.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(calls[0].body).toEqual({ name: "Oshxona", type: "indoor", icon: "kitchen" });
  });

  it("delete asks for confirmation first", async () => {
    const calls = mockFetch((_url, init) => (init.method === "DELETE" ? ok({ deleted: true }) : undefined));
    renderWithProviders(<RoomSheet open onClose={() => undefined} homeId="h1" room={rooms[0]} />);
    await userEvent.click(screen.getByRole("button", { name: "Bo'limni o'chirish" }));
    expect(calls).toHaveLength(0);
    expect(screen.getByRole("alert")).toHaveTextContent("Bo'limsiz");
    await userEvent.click(screen.getByRole("button", { name: "Ha, o'chirish" }));
    expect(calls[0]).toMatchObject({ method: "DELETE" });
    expect(calls[0].url).toContain("/rooms/r1");
  });
});
