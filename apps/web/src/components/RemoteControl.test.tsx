import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders, v } from "../test/utils";
import { RemoteControl } from "./RemoteControl";

const view = (buttons: string[] | null) => ({
  permission: "control_basic", risk: "low", config: { layout: "tv" },
  attributes: { buttons: buttons === null ? { value: null, source: "reported", quality: "unknown", ts: null } : v(buttons) },
}) as never;

describe("IR remote (ADR 0016)", () => {
  it("only learned buttons can be pressed; press sends the button", async () => {
    const send = vi.fn();
    renderWithProviders(<RemoteControl view={view(["power"])} send={send} disabled={false} pending={false} />);
    expect(screen.getByText("1 ta tugma o'rgatilgan")).toBeInTheDocument();
    expect(screen.getByTestId("rbtn-vol_up")).toBeDisabled();
    await userEvent.click(screen.getByTestId("rbtn-power"));
    expect(send).toHaveBeenCalledWith("remote", "press", { button: "power" });
  });

  it("learn mode: tapping asks the hub to listen for the original remote", async () => {
    const send = vi.fn();
    renderWithProviders(<RemoteControl view={view([])} send={send} disabled={false} pending={false} />);
    await userEvent.click(screen.getByRole("button", { name: /O'rgatish/ }));
    expect(screen.getByText(/asl pultni IR pultga qaratib/)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("rbtn-num_5"));
    expect(send).toHaveBeenCalledWith("remote", "learn", { button: "num_5" });
  });

  it("unknown list is not shown as zero buttons", () => {
    renderWithProviders(<RemoteControl view={view(null)} send={vi.fn()} disabled={false} pending={false} />);
    expect(screen.queryByText(/0 ta tugma/)).toBeNull();
    expect(screen.getByText("Noma'lum")).toBeInTheDocument();
  });
});
