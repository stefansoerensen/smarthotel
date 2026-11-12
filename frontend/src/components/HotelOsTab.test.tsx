import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as hotelOs from "../services/hotelOs";
import HotelOsTab from "./HotelOsTab";

const link = {
  hotel_os_property_code: null,
  enabled: false,
  comfort_setpoint: 21,
  eco_setpoint: 17,
  energy_price_eur_per_kwh: null,
  last_sync_at: null,
  last_sync_error: null,
  configured: true,
};

describe("HotelOsTab", () => {
  beforeEach(() => {
    vi.spyOn(hotelOs, "getLink").mockResolvedValue(link);
    vi.spyOn(hotelOs, "listFaults").mockResolvedValue({
      property_code: "HAM1",
      items: [{ kind: "RoomTooCold", severity: "Today", message: "Zimmer 101 zu kalt", unit_name: "101", since: null }],
    });
  });

  it("links the property and syncs", async () => {
    const save = vi.spyOn(hotelOs, "saveLink").mockResolvedValue({ ...link, hotel_os_property_code: "HAM", enabled: true });
    const sync = vi.spyOn(hotelOs, "sync").mockResolvedValue({ rooms_changed: 4, unmatched_units: ["999"] });
    render(<HotelOsTab propertyCode="HAM1" />);
    const form = await screen.findByRole("form", { name: "Verknüpfung" });
    await userEvent.type(within(form).getByLabelText("Hauscode im Hotel OS"), "HAM");
    await userEvent.click(within(form).getByRole("button", { name: "Speichern" }));
    expect(save).toHaveBeenCalledWith("HAM1", {
      hotel_os_property_code: "HAM",
      enabled: true,
      comfort_setpoint: 21,
      eco_setpoint: 17,
      energy_price_eur_per_kwh: null,
    });
    await userEvent.click(await screen.findByRole("button", { name: "Jetzt abgleichen" }));
    expect(sync).toHaveBeenCalledWith("HAM1");
    expect(await screen.findByRole("status")).toHaveTextContent("4 Zimmer geändert · ohne Zimmer im Haus: 999");
  });

  it("lists faults for the front desk", async () => {
    render(<HotelOsTab propertyCode="HAM1" />);
    const list = await screen.findByRole("list", { name: "Störungen" });
    expect(within(list).getByText("Zimmer 101 zu kalt")).toBeInTheDocument();
    expect(within(list).getByText("heute")).toBeInTheDocument();
  });

  it("says when the Railway variables are missing", async () => {
    vi.spyOn(hotelOs, "getLink").mockResolvedValue({ ...link, configured: false });
    render(<HotelOsTab propertyCode="HAM1" />);
    expect(await screen.findByText(/HOTEL_OS_URL/)).toBeInTheDocument();
  });
});
