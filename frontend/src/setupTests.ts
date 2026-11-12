import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { useAuthStore } from "./hooks/useAuthStore";

afterEach(() => {
  cleanup();
  localStorage.clear();
  useAuthStore.setState({ token: null, user: null });
});
