import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as hotelOs from "../services/hotelOs";
import OverviewBar from "./OverviewBar";

describe("OverviewBar", () => {
  it("shows the figures of the property", async () => {
    vi.spyOn(hotelOs, "getOverview").mockResolvedValue({
      rooms: { total: 3, occupied: 1, arriving: 1, vacant: 1, unknown: 0 },
      modes: { comfort: 1, preheat: 1, eco: 1 },
      avg_temperature_occupied: 20.4,
      faults: { total: 2, blocker: 0, today: 1, attention: 1 },
      gateways: { total: 1, online: 0, offline: 1, never: 0 },
      kwh_yesterday: 12.5,
      pending_commands: 4,
    });
    render(<OverviewBar propertyCode="HAM1" />);
    expect(await screen.findByText("1 belegt · 1 Anreise · 1 frei")).toBeInTheDocument();
    expect(screen.getByText("20,4 °C")).toBeInTheDocument();
    expect(screen.getByText("2 Störungen")).toBeInTheDocument();
    expect(screen.getByText("0 / 1 online")).toBeInTheDocument();
    expect(screen.getByText("12,5 kWh")).toBeInTheDocument();
    expect(screen.getByText("4 offene Befehle")).toBeInTheDocument();
  });
});
