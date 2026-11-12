import type { User } from "../types";
import { api } from "./api";

export async function login(username: string, password: string): Promise<string> {
  const { data } = await api.post<{ access_token: string }>("/auth/login", { username, password });
  return data.access_token;
}

export async function me(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
