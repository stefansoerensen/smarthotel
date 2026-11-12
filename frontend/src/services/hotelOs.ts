import type { Fault, HotelOsLink, HotelOsLinkInput, SyncResult } from "../types";
import { api } from "./api";

const base = (propertyCode: string) => `/properties/${encodeURIComponent(propertyCode)}`;

export async function getLink(propertyCode: string): Promise<HotelOsLink> {
  return (await api.get<HotelOsLink>(`${base(propertyCode)}/hotel-os`)).data;
}

export async function saveLink(propertyCode: string, input: HotelOsLinkInput): Promise<HotelOsLink> {
  return (await api.put<HotelOsLink>(`${base(propertyCode)}/hotel-os`, input)).data;
}

export async function sync(propertyCode: string): Promise<SyncResult> {
  return (await api.post<SyncResult>(`${base(propertyCode)}/hotel-os/sync`)).data;
}

export async function listFaults(propertyCode: string): Promise<{ property_code: string; items: Fault[] }> {
  return (await api.get<{ property_code: string; items: Fault[] }>(`${base(propertyCode)}/faults`)).data;
}
