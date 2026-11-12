import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as devices from "../services/devices";
import GatewaysPanel from "./GatewaysPanel";

describe("GatewaysPanel", () => {
  beforeEach(() => {
    vi.spyOn(devices, "listGateways").mockResolvedValue({
      items: [{ code: "GW-01", name: "Technik UG", status: "offline", last_seen_at: "2026-11-12T08:00:00Z", has_token: true }],
      total: 1,
    });
  });

  it("lists gateways with their status", async () => {
    render(<GatewaysPanel propertyCode="HAM1" />);
    const row = await screen.findByRole("listitem", { name: "Gateway GW-01" });
    expect(within(row).getByText("offline")).toBeInTheDocument();
  });

  it("registers a gateway with a suggested code", async () => {
    const register = vi
      .spyOn(devices, "registerGateway")
      .mockResolvedValue({ code: "TECHNIK-EG", name: "Technik EG", status: "provisioned", last_seen_at: null, has_token: false });
    render(<GatewaysPanel propertyCode="HAM1" />);
    const form = await screen.findByRole("form", { name: "Gateway registrieren" });
    await userEvent.type(within(form).getByLabelText("Name"), "Technik EG");
    expect(within(form).getByLabelText("Code")).toHaveValue("TECHNIK-EG");
    await userEvent.click(within(form).getByRole("button", { name: "Gateway registrieren" }));
    expect(register).toHaveBeenCalledWith("HAM1", { code: "TECHNIK-EG", name: "Technik EG" });
  });

  it("shows a new token once with the command to run the gateway", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(devices, "createGatewayToken").mockResolvedValue({ gateway_code: "GW-01", token: "tok-123" });
    render(<GatewaysPanel propertyCode="HAM1" />);
    const row = await screen.findByRole("listitem", { name: "Gateway GW-01" });
    await userEvent.click(within(row).getByRole("button", { name: "Neuen Token erzeugen" }));
    expect(window.confirm).toHaveBeenCalled();
    const shown = await screen.findByRole("region", { name: "Token für GW-01" });
    expect(within(shown).getByText(/EDGE_TOKEN=tok-123/)).toBeInTheDocument();
    await userEvent.click(within(shown).getByRole("button", { name: "Ausblenden" }));
    expect(screen.queryByText(/tok-123/)).not.toBeInTheDocument();
  });
});
