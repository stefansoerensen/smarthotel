import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Room } from "../types";
import RoomTile from "./RoomTile";

function point(key: string, value: number | null, writable = false, unit: string | null = null) {
  return { key, label: key, kind: key, unit, writable, device_code: null, value, value_at: null, source: null, desired: null, desired_at: null };
}

const room: Room = {
  code: "101",
  name: "Zimmer 101",
  floor: "1",
  room_type_code: "STD",
  gateway_code: null,
  occupancy: null,
  mode: null,
  reservation_code: null,
  points: [
    point("temperature", 20.4, false, "°C"),
    point("setpoint", 21, true, "°C"),
    point("window", 1),
    point("presence", 0),
    point("valve", 0, true, "%"),
    point("heat_meter", 1.234, false, "kWh"),
  ],
};

describe("RoomTile", () => {
  it("shows the state of the room", () => {
    render(<RoomTile room={room} onSetpoint={vi.fn()} onSimulate={vi.fn()} />);
    expect(screen.getByText("101")).toBeInTheDocument();
    expect(screen.getByText("20,4 °C")).toBeInTheDocument();
    expect(screen.getByText("Soll 21,0 °C")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fenster offen" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "abwesend" })).toBeInTheDocument();
    expect(screen.getByText("Ventil 0 %")).toBeInTheDocument();
    expect(screen.getByText("1,23 kWh")).toBeInTheDocument();
  });

  it("raises the set point by half a degree", async () => {
    const onSetpoint = vi.fn().mockResolvedValue(undefined);
    render(<RoomTile room={room} onSetpoint={onSetpoint} onSimulate={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Sollwert erhöhen" }));
    expect(onSetpoint).toHaveBeenCalledWith(21.5);
  });

  it("toggles window and presence through the simulator", async () => {
    const onSimulate = vi.fn().mockResolvedValue(undefined);
    render(<RoomTile room={room} onSetpoint={vi.fn()} onSimulate={onSimulate} />);
    await userEvent.click(screen.getByRole("button", { name: "Fenster offen" }));
    expect(onSimulate).toHaveBeenCalledWith({ window: false });
    await userEvent.click(screen.getByRole("button", { name: "abwesend" }));
    expect(onSimulate).toHaveBeenCalledWith({ presence: true });
  });

  it("shows a set point that waits for the gateway and hides simulator toggles of edge rooms", () => {
    const edgeRoom: Room = {
      ...room,
      gateway_code: "GW-01",
      points: room.points.map((p) => (p.key === "setpoint" ? { ...p, desired: 22 } : p)),
    };
    render(<RoomTile room={edgeRoom} onSetpoint={vi.fn()} onSimulate={vi.fn()} />);
    expect(screen.getByText("Soll 22,0 °C")).toBeInTheDocument();
    expect(screen.getByText("ausstehend")).toBeInTheDocument();
    expect(screen.getByText("Fenster offen")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Fenster offen" })).not.toBeInTheDocument();
    expect(screen.getByText("GW-01")).toBeInTheDocument();
  });

  it("shows occupancy and mode from the Hotel OS", () => {
    render(
      <RoomTile
        room={{ ...room, occupancy: "arriving", mode: "preheat", reservation_code: "R1" }}
        onSetpoint={vi.fn()}
        onSimulate={vi.fn()}
      />,
    );
    expect(screen.getByText("Anreise heute · Vorheizen")).toBeInTheDocument();
  });
});
