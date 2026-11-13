import type { Page, UserEntry, UserInput, UserPatch } from "../types";
import { api } from "./api";

export async function listUsers(): Promise<Page<UserEntry>> {
  return (await api.get<Page<UserEntry>>("/users", { params: { limit: 500 } })).data;
}

export async function createUser(input: UserInput): Promise<UserEntry> {
  return (await api.post<UserEntry>("/users", input)).data;
}

export async function patchUser(username: string, changes: UserPatch): Promise<UserEntry> {
  return (await api.patch<UserEntry>(`/users/${encodeURIComponent(username)}`, changes)).data;
}

export async function changeOwnPassword(oldPassword: string, newPassword: string): Promise<void> {
  await api.post("/auth/password", { old_password: oldPassword, new_password: newPassword });
}
