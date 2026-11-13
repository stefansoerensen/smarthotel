import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../hooks/useAuthStore";
import * as estate from "../services/estate";
import * as usersService from "../services/users";
import UsersPage from "./UsersPage";

describe("UsersPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ token: "t", user: { username: "admin", role: "admin", tenant_code: null } });
    vi.spyOn(usersService, "listUsers").mockResolvedValue({
      items: [
        { username: "admin", role: "admin", tenant_code: null, is_active: true },
        { username: "rezeption", role: "operator", tenant_code: "GRP", is_active: true },
      ],
      total: 2,
    });
    vi.spyOn(estate, "listTenants").mockResolvedValue({ items: [{ code: "GRP", name: "Gruppe", is_active: true }], total: 1 });
  });

  it("creates an operator for a tenant", async () => {
    const create = vi.spyOn(usersService, "createUser").mockResolvedValue({
      username: "technik",
      role: "operator",
      tenant_code: "GRP",
      is_active: true,
    });
    render(<MemoryRouter><UsersPage /></MemoryRouter>);
    const form = await screen.findByRole("form", { name: "Benutzer anlegen" });
    await userEvent.type(within(form).getByLabelText("Benutzername"), "technik");
    await userEvent.type(within(form).getByLabelText("Startpasswort"), "Start12345!");
    await userEvent.click(within(form).getByRole("button", { name: "Benutzer anlegen" }));
    expect(create).toHaveBeenCalledWith({ username: "technik", password: "Start12345!", role: "operator", tenant_code: "GRP" });
  });

  it("deactivates a user after confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const patch = vi.spyOn(usersService, "patchUser").mockResolvedValue({
      username: "rezeption",
      role: "operator",
      tenant_code: "GRP",
      is_active: false,
    });
    render(<MemoryRouter><UsersPage /></MemoryRouter>);
    const row = await screen.findByRole("row", { name: /rezeption/ });
    await userEvent.click(within(row).getByRole("button", { name: "Deaktivieren" }));
    expect(patch).toHaveBeenCalledWith("rezeption", { is_active: false });
  });

  it("resets a password", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("Neu12345678!");
    const patch = vi.spyOn(usersService, "patchUser").mockResolvedValue({
      username: "rezeption",
      role: "operator",
      tenant_code: "GRP",
      is_active: true,
    });
    render(<MemoryRouter><UsersPage /></MemoryRouter>);
    const row = await screen.findByRole("row", { name: /rezeption/ });
    await userEvent.click(within(row).getByRole("button", { name: "Passwort zurücksetzen" }));
    expect(patch).toHaveBeenCalledWith("rezeption", { password: "Neu12345678!" });
  });
});
