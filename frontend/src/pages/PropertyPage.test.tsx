import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as devices from "../services/devices";
import * as estate from "../services/estate";
import { useAuthStore } from "../hooks/useAuthStore";
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

  it("registers a device from kind, location and protocol and reloads the list", async () => {
    const register = vi.spyOn(devices, "registerDevice").mockResolvedValue(valve);
    renderPage();
    await screen.findByText("Heizventil 101");
    await userEvent.type(screen.getByLabelText("Ort"), "102");
    expect(screen.getByText("Heizventil 102")).toBeInTheDocument();
    expect(screen.getByLabelText("Code")).toHaveValue("102-VALVE");
    await userEvent.click(screen.getByRole("button", { name: "Gerät anlegen" }));
    expect(register).toHaveBeenCalledWith("HAM1", {
      code: "102-VALVE",
      name: "Heizventil 102",
      kind: "valve",
      protocol: "knx",
      location: "102",
    });
    expect(devices.listDevices).toHaveBeenCalledTimes(2);
  });

  it("asks for the location with a hint and no postal or bus address", async () => {
    renderPage();
    await screen.findByText("Heizventil 101");
    expect(screen.getByLabelText("Ort")).toHaveAttribute("placeholder", "Zimmernummer, Flur o. ä.");
    expect(screen.queryByLabelText(/adresse/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
  });

  it("needs a location before a device can be registered", async () => {
    renderPage();
    await screen.findByText("Heizventil 101");
    expect(screen.getByRole("button", { name: "Gerät anlegen" })).toBeDisabled();
  });

  it("edits a device in its row and reloads", async () => {
    const patch = vi.spyOn(devices, "patchDevice").mockResolvedValue(valve);
    renderPage();
    const row = await screen.findByRole("row", { name: /Heizventil 101/ });
    await userEvent.click(within(row).getByRole("button", { name: "Bearbeiten" }));
    const editRow = screen.getByRole("row", { name: /Gerät 101-V bearbeiten/ });
    const location = within(editRow).getByLabelText("Ort");
    await userEvent.clear(location);
    await userEvent.type(location, "105");
    await userEvent.click(within(editRow).getByRole("button", { name: "Speichern" }));
    expect(patch).toHaveBeenCalledWith("HAM1", "101-V", {
      kind: "valve",
      protocol: "knx",
      location: "105",
      name: "Heizventil 105",
    });
    expect(devices.listDevices).toHaveBeenCalledTimes(2);
  });

  it("retires a device after confirmation", async () => {
    const retire = vi.spyOn(devices, "retireDevice").mockResolvedValue({ ...valve, status: "retired" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();
    const row = await screen.findByRole("row", { name: /Heizventil 101/ });
    await userEvent.click(within(row).getByRole("button", { name: "Außer Betrieb nehmen" }));
    expect(window.confirm).toHaveBeenCalled();
    expect(retire).toHaveBeenCalledWith("HAM1", "101-V");
  });

  it("lets an admin edit the property", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    const patch = vi.spyOn(estate, "patchProperty").mockResolvedValue({
      code: "HAM1",
      tenant_code: "GRP",
      name: "Hamburg Hafen",
      time_zone: "Europe/Berlin",
      street: "Kai 1",
      postal_code: "20457",
      city: "Hamburg",
      country_code: "DE",
    });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Haus bearbeiten" }));
    const form = screen.getByRole("form", { name: "Haus bearbeiten" });
    const name = within(form).getByLabelText("Name");
    await userEvent.clear(name);
    await userEvent.type(name, "Hamburg Hafen");
    await userEvent.type(within(form).getByLabelText("Straße"), "Kai 1");
    await userEvent.type(within(form).getByLabelText("PLZ"), "20457");
    await userEvent.click(within(form).getByRole("button", { name: "Speichern" }));
    expect(patch).toHaveBeenCalledWith("HAM1", {
      name: "Hamburg Hafen",
      street: "Kai 1",
      postal_code: "20457",
      city: "Hamburg",
    });
    expect(await screen.findByRole("heading", { name: "Hamburg Hafen" })).toBeInTheDocument();
  });

  it("does not offer property editing to operators", async () => {
    useAuthStore.setState({ token: "t", user: { username: "op", role: "operator", tenant_code: "GRP" } });
    renderPage();
    await screen.findByText("Heizventil 101");
    expect(screen.queryByRole("button", { name: "Haus bearbeiten" })).not.toBeInTheDocument();
  });
});
