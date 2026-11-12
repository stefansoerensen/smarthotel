import { render, screen } from "@testing-library/react";
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
});
