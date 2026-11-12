import { create } from "zustand";
import { configureAuth } from "../services/api";
import type { User } from "../types";

const STORAGE_KEY = "smarthotel.token";

function readToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

interface AuthState {
  token: string | null;
  user: User | null;
  setSession: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: readToken(),
  user: null,
  setSession: (token, user) => {
    try {
      localStorage.setItem(STORAGE_KEY, token);
    } catch {
      /* storage unavailable: the session lives in memory only */
    }
    set({ token, user });
  },
  logout: () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* nothing stored */
    }
    set({ token: null, user: null });
  },
}));

configureAuth(
  () => useAuthStore.getState().token,
  () => useAuthStore.getState().logout(),
);
