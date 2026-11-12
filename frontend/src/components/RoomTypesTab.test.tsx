import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as devicesService from "../services/devices";
import * as twin from "../services/twin";
import type { Catalogue, RoomType } from "../types";
import RoomTypesTab from "./RoomTypesTab";

const catalogue: Catalogue = {
  kinds: [
    { kind: "temperature_sensor", label: "Raumtemperatur", safety: false, writable: false },
    { kind: "fan_coil", label: "Fan-Coil", safety: false, writable: true },
  ],
  protocols: { knx: "KNX/IP" },
};

const std: RoomType = {
  code: "STD",
  name: "Standardzimmer",
  description: null,
  points: [
    { key: "temperature", label: "Raumtemperatur", kind: "temperature_sensor", protocol: "knx", unit: "°C", writable: false },
  ],
};

describe("RoomTypesTab", () => {
  beforeEach(() => {
    vi.spyOn(twin, "listRoomTypes").mockResolvedValue({ items: [std], total: 1 });
    vi.spyOn(devicesService, "listGateways").mockResolvedValue({ items: [], total: 0 });
  });

  it("creates a room type with the standard points and a suggested code", async () => {
    const create = vi.spyOn(twin, "createRoomType").mockResolvedValue({ ...std, code: "SUITE", name: "Suite" });
    render(<RoomTypesTab propertyCode="HAM1" catalogue={catalogue} />);
    const form = await screen.findByRole("form", { name: "Raumtyp anlegen" });
    await userEvent.type(within(form).getByLabelText("Name"), "Suite");
    expect(within(form).getByLabelText("Code")).toHaveValue("SUITE");
    await userEvent.click(within(form).getByRole("button", { name: "Raumtyp anlegen" }));
    expect(create).toHaveBeenCalledWith("HAM1", { code: "SUITE", name: "Suite", standard_points: true });
  });

  it("rolls a room type out to a range of rooms and reports the result", async () => {
    const rollout = vi.spyOn(twin, "rollout").mockResolvedValue({
      rooms_created: 3,
      rooms_unchanged: 0,
      devices_created: 21,
      conflicts: [],
    });
    render(<RoomTypesTab propertyCode="HAM1" catalogue={catalogue} />);
    const form = await screen.findByRole("form", { name: "Ausrollen" });
    await userEvent.type(within(form).getByLabelText("Zimmer"), "101-103");
    await userEvent.type(within(form).getByLabelText("Etage"), "1");
    expect(within(form).getByText("3 Zimmer")).toBeInTheDocument();
    await userEvent.click(within(form).getByRole("button", { name: "Ausrollen" }));
    expect(rollout).toHaveBeenCalledWith("HAM1", {
      room_type_code: "STD",
      room_codes: ["101", "102", "103"],
      floor: "1",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("3 Zimmer angelegt, 21 Geräte registriert");
  });

  it("adds a point to a room type with a key from its label", async () => {
    const add = vi.spyOn(twin, "addPoint").mockResolvedValue(std);
    render(<RoomTypesTab propertyCode="HAM1" catalogue={catalogue} />);
    const card = await screen.findByRole("region", { name: "Raumtyp STD" });
    await userEvent.click(within(card).getByRole("button", { name: "Datenpunkt hinzufügen" }));
    await userEvent.type(within(card).getByLabelText("Bezeichnung"), "Fan-Coil Bad");
    await userEvent.selectOptions(within(card).getByLabelText("Art"), "fan_coil");
    await userEvent.click(within(card).getByRole("button", { name: "Hinzufügen" }));
    expect(add).toHaveBeenCalledWith("HAM1", "STD", {
      key: "fan_coil_bad",
      label: "Fan-Coil Bad",
      kind: "fan_coil",
      protocol: "knx",
      writable: true,
    });
  });

  it("rolls out behind a gateway when one is chosen", async () => {
    vi.spyOn(devicesService, "listGateways").mockResolvedValue({
      items: [{ code: "GW-01", name: "Technik", status: "online", last_seen_at: null, has_token: true }],
      total: 1,
    });
    const rollout = vi
      .spyOn(twin, "rollout")
      .mockResolvedValue({ rooms_created: 1, rooms_unchanged: 0, devices_created: 1, conflicts: [] });
    render(<RoomTypesTab propertyCode="HAM1" catalogue={catalogue} />);
    const form = await screen.findByRole("form", { name: "Ausrollen" });
    await userEvent.type(within(form).getByLabelText("Zimmer"), "301");
    await userEvent.selectOptions(await within(form).findByLabelText("Gateway"), "GW-01");
    await userEvent.click(within(form).getByRole("button", { name: "Ausrollen" }));
    expect(rollout).toHaveBeenCalledWith("HAM1", { room_type_code: "STD", room_codes: ["301"], gateway_code: "GW-01" });
  });
});
