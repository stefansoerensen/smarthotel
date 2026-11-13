import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as devices from "../services/devices";
import CommandsPanel from "./CommandsPanel";

describe("CommandsPanel", () => {
  it("lists commands with German status", async () => {
    vi.spyOn(devices, "listCommands").mockResolvedValue({
      items: [
        { id: "1", device_code: "101-SETPOINT", point_key: "setpoint", value: 21.5, status: "done", created_at: "2026-11-12T08:00:00Z", sent_at: null, acked_at: null, detail: null },
        { id: "2", device_code: "101-SMOKE", point_key: "x", value: 1, status: "refused", created_at: "2026-11-12T08:00:00Z", sent_at: null, acked_at: null, detail: "device is not controllable" },
      ],
      total: 2,
    });
    render(<CommandsPanel propertyCode="HAM1" />);
    const list = await screen.findByRole("table", { name: "Befehle" });
    expect(within(list).getByText("erledigt")).toBeInTheDocument();
    expect(within(list).getByText("abgelehnt")).toBeInTheDocument();
    expect(within(list).getByText("device is not controllable")).toBeInTheDocument();
  });
});
