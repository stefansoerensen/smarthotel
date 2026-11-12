import type { EnergyNights, EnergySeries } from "../types";
import { api } from "./api";

const base = (propertyCode: string) => `/properties/${encodeURIComponent(propertyCode)}/energy`;

export async function getSeries(
  propertyCode: string,
  from: string,
  to: string,
  resolution: "15min" | "day",
): Promise<EnergySeries> {
  return (await api.get<EnergySeries>(base(propertyCode), { params: { from, to, resolution } })).data;
}

export async function getNights(propertyCode: string, from: string, to: string): Promise<EnergyNights> {
  return (await api.get<EnergyNights>(`${base(propertyCode)}/nights`, { params: { from, to } })).data;
}
