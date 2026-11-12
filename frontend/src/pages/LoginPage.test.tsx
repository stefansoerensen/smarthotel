import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../hooks/useAuthStore";
import * as auth from "../services/auth";
import LoginPage from "./LoginPage";

describe("LoginPage", () => {
  it("stores the session after a successful login", async () => {
    vi.spyOn(auth, "login").mockResolvedValue("tok");
    vi.spyOn(auth, "me").mockResolvedValue({ username: "anna", role: "admin", tenant_code: null });
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText("Benutzer"), "anna");
    await userEvent.type(screen.getByLabelText("Passwort"), "Secret123!");
    await userEvent.click(screen.getByRole("button", { name: "Anmelden" }));
    expect(auth.login).toHaveBeenCalledWith("anna", "Secret123!");
    expect(useAuthStore.getState().token).toBe("tok");
    expect(useAuthStore.getState().user?.username).toBe("anna");
  });

  it("shows the error when the login fails", async () => {
    vi.spyOn(auth, "login").mockRejectedValue({
      status: 401,
      code: "auth.invalid_credentials",
      message: "Invalid username or password",
    });
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText("Benutzer"), "anna");
    await userEvent.type(screen.getByLabelText("Passwort"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Anmelden" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Benutzer oder Passwort falsch");
  });
});
