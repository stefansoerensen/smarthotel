import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as energy from "../services/energy";
import EnergyTab from "./EnergyTab";

describe("EnergyTab", () => {
  beforeEach(() => {
    vi.spyOn(energy, "getSeries").mockResolvedValue({
      resolution: "day",
      buckets: [
        { start: "2026-11-11T23:00:00Z", kwh: 2 },
        { start: "2026-11-12T23:00:00Z", kwh: 3.9 },
      ],
      rooms: [
        { room_code: "101", kwh: 5.5 },
        { room_code: "102", kwh: 0.4 },
      ],
      total_kwh: 5.9,
    });
    vi.spyOn(energy, "getNights").mockResolvedValue({
      nights: [
        { date: "2026-11-12", room_code: "101", occupied: true, reservation_code: "R1", kwh: 5 },
        { date: "2026-11-12", room_code: "102", occupied: false, reservation_code: null, kwh: 0.4 },
      ],
      summary: {
        occupied_nights: 1,
        kwh_occupied: 5,
        kwh_vacant: 0.4,
        kwh_per_occupied_night: 5,
        price_eur_per_kwh: "0.1200",
        cost_per_occupied_night_eur: "0.60",
      },
    });
  });

  it("shows totals, kWh per occupied night and its cost", async () => {
    render(<EnergyTab propertyCode="HAM1" today="2026-11-13" />);
    const figures = await screen.findByRole("list", { name: "Kennzahlen" });
    expect(within(figures).getByText("5,9 kWh")).toBeInTheDocument();
    expect(within(figures).getByText("5,0 kWh")).toBeInTheDocument();
    expect(within(figures).getByText("0,60 €")).toBeInTheDocument();
    expect(energy.getSeries).toHaveBeenCalledWith("HAM1", "2026-11-07", "2026-11-13", "day");
  });

  it("draws one bar per day and lists nights per room", async () => {
    render(<EnergyTab propertyCode="HAM1" today="2026-11-13" />);
    const chart = await screen.findByRole("list", { name: "Verbrauch je Tag" });
    expect(within(chart).getAllByRole("listitem")).toHaveLength(2);
    const table = screen.getByRole("table", { name: "Nächte" });
    expect(within(table).getByText("R1")).toBeInTheDocument();
  });

  it("reloads for another range", async () => {
    render(<EnergyTab propertyCode="HAM1" today="2026-11-13" />);
    await screen.findByRole("list", { name: "Kennzahlen" });
    await userEvent.click(screen.getByRole("button", { name: "30 Tage" }));
    expect(energy.getSeries).toHaveBeenLastCalledWith("HAM1", "2026-10-15", "2026-11-13", "day");
  });
});
