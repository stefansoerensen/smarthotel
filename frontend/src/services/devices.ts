import type { Catalogue, Device, DeviceInput, DevicePatch, Page } from "../types";
import { api } from "./api";

export async function getCatalogue(): Promise<Catalogue> {
  return (await api.get<Catalogue>("/device-catalogue")).data;
}

export async function listDevices(propertyCode: string, kind?: string): Promise<Page<Device>> {
  const params: Record<string, string | number> = { limit: 500 };
  if (kind) {
    params.kind = kind;
  }
  const url = `/properties/${encodeURIComponent(propertyCode)}/devices`;
  return (await api.get<Page<Device>>(url, { params })).data;
}

export async function registerDevice(propertyCode: string, input: DeviceInput): Promise<Device> {
  const url = `/properties/${encodeURIComponent(propertyCode)}/devices`;
  return (await api.post<Device>(url, input)).data;
}

function deviceUrl(propertyCode: string, deviceCode: string): string {
  return `/properties/${encodeURIComponent(propertyCode)}/devices/${encodeURIComponent(deviceCode)}`;
}

export async function patchDevice(
  propertyCode: string,
  deviceCode: string,
  changes: DevicePatch,
): Promise<Device> {
  return (await api.patch<Device>(deviceUrl(propertyCode, deviceCode), changes)).data;
}

/** Take a device out of service; it stays in the registry with status "retired". */
export async function retireDevice(propertyCode: string, deviceCode: string): Promise<Device> {
  return (await api.delete<Device>(deviceUrl(propertyCode, deviceCode))).data;
}
