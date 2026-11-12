import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../hooks/useAuthStore";
import * as estate from "../services/estate";
import PropertiesPage from "./PropertiesPage";

function renderPage() {
  render(
    <MemoryRouter>
      <PropertiesPage />
    </MemoryRouter>,
  );
}

describe("PropertiesPage", () => {
  beforeEach(() => {
    vi.spyOn(estate, "listProperties").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(estate, "listTenants").mockResolvedValue({ items: [], total: 0 });
  });

  it("lets an admin create a tenant and reloads", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    const create = vi
      .spyOn(estate, "createTenant")
      .mockResolvedValue({ code: "GRP", name: "Hotelgruppe Nord", is_active: true });
    renderPage();
    const form = await screen.findByRole("form", { name: "Mandant anlegen" });
    await userEvent.type(screen.getByLabelText("Mandanten-Code"), "GRP");
    await userEvent.type(screen.getByLabelText("Mandanten-Name"), "Hotelgruppe Nord");
    await userEvent.click(screen.getByRole("button", { name: "Mandant anlegen" }));
    expect(form).toBeInTheDocument();
    expect(create).toHaveBeenCalledWith({ code: "GRP", name: "Hotelgruppe Nord" });
    expect(estate.listTenants).toHaveBeenCalledTimes(2);
  });

  it("shows the conflict message from the API", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    vi.spyOn(estate, "createTenant").mockRejectedValue({
      status: 409,
      code: "tenant.code_taken",
      message: "Tenant code 'GRP' is taken",
    });
    renderPage();
    await userEvent.type(await screen.findByLabelText("Mandanten-Code"), "GRP");
    await userEvent.type(screen.getByLabelText("Mandanten-Name"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Mandant anlegen" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Mandanten-Code ist schon vergeben");
  });

  it("hides the tenant form from operators", async () => {
    useAuthStore.setState({ token: "t", user: { username: "op", role: "operator", tenant_code: "GRP" } });
    renderPage();
    await screen.findByText("Noch kein Haus angelegt.");
    expect(screen.queryByRole("form", { name: "Mandant anlegen" })).not.toBeInTheDocument();
  });

  it("suggests the tenant code from the name until the code is edited", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    const create = vi
      .spyOn(estate, "createTenant")
      .mockResolvedValue({ code: "HOTELGRUPPE-NORD", name: "Hotelgruppe Nord", is_active: true });
    renderPage();
    await userEvent.type(await screen.findByLabelText("Mandanten-Name"), "Hotelgruppe Nord");
    expect(screen.getByLabelText("Mandanten-Code")).toHaveValue("HOTELGRUPPE-NORD");
    await userEvent.click(screen.getByRole("button", { name: "Mandant anlegen" }));
    expect(create).toHaveBeenCalledWith({ code: "HOTELGRUPPE-NORD", name: "Hotelgruppe Nord" });
  });

  it("keeps a code the user typed", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    renderPage();
    await userEvent.type(await screen.findByLabelText("Mandanten-Code"), "GRP");
    await userEvent.type(screen.getByLabelText("Mandanten-Name"), "Hotelgruppe Nord");
    expect(screen.getByLabelText("Mandanten-Code")).toHaveValue("GRP");
  });

  it("suggests a property code that is not taken yet", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    vi.spyOn(estate, "listTenants").mockResolvedValue({
      items: [{ code: "GRP", name: "Gruppe", is_active: true }],
      total: 1,
    });
    vi.spyOn(estate, "listProperties").mockResolvedValue({
      items: [
        {
          code: "NEUBAU-HAMBURG",
          tenant_code: "GRP",
          name: "Neubau Hamburg",
          time_zone: "Europe/Berlin",
          street: null,
          postal_code: null,
          city: null,
          country_code: "DE",
        },
      ],
      total: 1,
    });
    renderPage();
    const form = await screen.findByRole("form", { name: "Haus anlegen" });
    await userEvent.type(within(form).getByLabelText("Name"), "Neubau Hamburg");
    expect(within(form).getByLabelText("Code")).toHaveValue("NEUBAU-HAMBURG-2");
  });

  it("lets an admin rename a tenant", async () => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    vi.spyOn(estate, "listTenants").mockResolvedValue({
      items: [{ code: "GRP", name: "Gruppe", is_active: true }],
      total: 1,
    });
    const patch = vi
      .spyOn(estate, "patchTenant")
      .mockResolvedValue({ code: "GRP", name: "Gruppe Nord", is_active: true });
    renderPage();
    const item = await screen.findByRole("listitem", { name: "Mandant GRP" });
    await userEvent.click(within(item).getByRole("button", { name: "Umbenennen" }));
    const input = within(item).getByLabelText("Name von GRP");
    await userEvent.clear(input);
    await userEvent.type(input, "Gruppe Nord");
    await userEvent.click(within(item).getByRole("button", { name: "Speichern" }));
    expect(patch).toHaveBeenCalledWith("GRP", { name: "Gruppe Nord" });
    expect(estate.listTenants).toHaveBeenCalledTimes(2);
  });
});
