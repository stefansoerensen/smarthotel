import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as devices from "../services/devices";
import * as estate from "../services/estate";
import type { Device } from "../types";
import PropertyPage from "./PropertyPage";

const valve: Device = {
  code: "101-V",
  name: "Heizventil 101",
  kind: "valve",
  protocol: "knx",
  address: "1/2/3",
  location: "101",
  gateway_code: null,
  controllable: true,
  safety: false,
  status: "active",
};
const smoke: Device = { ...valve, code: "101-S", name: "Rauchmelder 101", kind: "smoke_detector", controllable: false, safety: true };

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/properties/HAM1"]}>
      <Routes>
        <Route path="/properties/:code" element={<PropertyPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PropertyPage", () => {
  beforeEach(() => {
    vi.spyOn(estate, "getProperty").mockResolvedValue({
      code: "HAM1",
      tenant_code: "GRP",
      name: "Neubau Hamburg",
      time_zone: "Europe/Berlin",
      street: null,
      postal_code: null,
      city: "Hamburg",
      country_code: "DE",
    });
    vi.spyOn(devices, "getCatalogue").mockResolvedValue({
      kinds: [
        { kind: "valve", label: "Heizventil", safety: false },
        { kind: "smoke_detector", label: "Rauchmelder", safety: true },
      ],
      protocols: { knx: "KNX/IP", bacnet: "BACnet/IP" },
    });
    vi.spyOn(devices, "listDevices").mockResolvedValue({ items: [valve, smoke], total: 2 });
  });

  it("lists the registry and marks safety devices read only", async () => {
    renderPage();
    const row = await screen.findByRole("row", { name: /Rauchmelder 101/ });
    expect(within(row).getByText("nur lesen")).toBeInTheDocument();
    const valveRow = screen.getByRole("row", { name: /Heizventil 101/ });
    expect(within(valveRow).getByText("steuerbar")).toBeInTheDocument();
  });

  it("registers a device and reloads the list", async () => {
    const register = vi.spyOn(devices, "registerDevice").mockResolvedValue(valve);
    renderPage();
    await screen.findByText("Heizventil 101");
    await userEvent.type(screen.getByLabelText("Code"), "102-V");
    await userEvent.type(screen.getByLabelText("Name"), "Heizventil 102");
    await userEvent.type(screen.getByLabelText("Ort"), "102");
    await userEvent.type(screen.getByLabelText("Busadresse (optional)"), "1/2/4");
    await userEvent.click(screen.getByRole("button", { name: "Gerät anlegen" }));
    expect(register).toHaveBeenCalledWith("HAM1", {
      code: "102-V",
      name: "Heizventil 102",
      kind: "valve",
      protocol: "knx",
      location: "102",
      address: "1/2/4",
    });
    expect(devices.listDevices).toHaveBeenCalledTimes(2);
  });

  it("suggests the device code from location and kind", async () => {
    const register = vi.spyOn(devices, "registerDevice").mockResolvedValue(valve);
    renderPage();
    await screen.findByText("Heizventil 101");
    await userEvent.type(screen.getByLabelText("Ort"), "101");
    expect(screen.getByLabelText("Code")).toHaveValue("101-VALVE");
    await userEvent.type(screen.getByLabelText("Name"), "Heizventil 101 Bad");
    await userEvent.click(screen.getByRole("button", { name: "Gerät anlegen" }));
    expect(register).toHaveBeenCalledWith("HAM1", expect.objectContaining({ code: "101-VALVE" }));
  });

  it("suggests the device name from kind and location", async () => {
    const register = vi.spyOn(devices, "registerDevice").mockResolvedValue(valve);
    renderPage();
    await screen.findByText("Heizventil 101");
    await userEvent.type(screen.getByLabelText("Ort"), "102");
    expect(screen.getByLabelText("Name")).toHaveValue("Heizventil 102");
    await userEvent.click(screen.getByRole("button", { name: "Gerät anlegen" }));
    expect(register).toHaveBeenCalledWith("HAM1", {
      code: "102-VALVE",
      name: "Heizventil 102",
      kind: "valve",
      protocol: "knx",
      location: "102",
      address: undefined,
    });
  });

  it("keeps a name the user typed", async () => {
    renderPage();
    await screen.findByText("Heizventil 101");
    await userEvent.type(screen.getByLabelText("Name"), "Ventil Bad");
    await userEvent.type(screen.getByLabelText("Ort"), "103");
    expect(screen.getByLabelText("Name")).toHaveValue("Ventil Bad");
  });

  it("shows the bus address format of the chosen protocol", async () => {
    renderPage();
    await screen.findByText("Heizventil 101");
    expect(screen.getByLabelText("Busadresse (optional)")).toHaveAttribute("placeholder", "KNX-Gruppenadresse, z. B. 1/2/3");
    await userEvent.selectOptions(screen.getByLabelText("Protokoll"), "bacnet");
    expect(screen.getByLabelText("Busadresse (optional)")).toHaveAttribute("placeholder", "Geräte-ID:Objekt, z. B. 1001:analog-input,3");
  });
});
