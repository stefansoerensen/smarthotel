import type {
  Page,
  Property,
  PropertyInput,
  PropertyPatch,
  Tenant,
  TenantInput,
  TenantPatch,
} from "../types";
import { api } from "./api";

export async function listTenants(): Promise<Page<Tenant>> {
  return (await api.get<Page<Tenant>>("/tenants", { params: { limit: 500 } })).data;
}

export async function listProperties(): Promise<Page<Property>> {
  return (await api.get<Page<Property>>("/properties", { params: { limit: 500 } })).data;
}

export async function getProperty(code: string): Promise<Property> {
  return (await api.get<Property>(`/properties/${encodeURIComponent(code)}`)).data;
}

export async function createProperty(input: PropertyInput): Promise<Property> {
  return (await api.post<Property>("/properties", input)).data;
}

export async function createTenant(input: TenantInput): Promise<Tenant> {
  return (await api.post<Tenant>("/tenants", input)).data;
}

export async function patchTenant(code: string, changes: TenantPatch): Promise<Tenant> {
  return (await api.patch<Tenant>(`/tenants/${encodeURIComponent(code)}`, changes)).data;
}

export async function patchProperty(code: string, changes: PropertyPatch): Promise<Property> {
  return (await api.patch<Property>(`/properties/${encodeURIComponent(code)}`, changes)).data;
}
