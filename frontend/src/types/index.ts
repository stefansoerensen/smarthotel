/** All shared types of the frontend. Other files import them from here. */

export interface Page<T> {
  items: T[];
  total: number;
}

export interface ApiError {
  status: number;
  code: string | null;
  message: string;
}

export interface User {
  username: string;
  role: "admin" | "operator";
  tenant_code: string | null;
}

export interface Tenant {
  code: string;
  name: string;
  is_active: boolean;
}

export interface TenantInput {
  code: string;
  name: string;
}

export interface TenantPatch {
  name: string;
}

export interface Property {
  code: string;
  tenant_code: string;
  name: string;
  time_zone: string;
  street: string | null;
  postal_code: string | null;
  city: string | null;
  country_code: string;
}

export interface PropertyInput {
  tenant_code: string;
  code: string;
  name: string;
  city?: string;
}

export interface PropertyPatch {
  name: string;
  street: string | null;
  postal_code: string | null;
  city: string | null;
}

export interface DevicePatch {
  kind: string;
  protocol: string;
  location: string;
  name: string;
}

export interface Device {
  code: string;
  name: string;
  kind: string;
  protocol: string;
  address: string | null;
  location: string | null;
  gateway_code: string | null;
  controllable: boolean;
  safety: boolean;
  status: string;
}

export interface DeviceInput {
  code: string;
  name: string;
  kind: string;
  protocol: string;
  address?: string;
  location?: string;
}

export interface DeviceKind {
  kind: string;
  label: string;
  safety: boolean;
}

export interface Catalogue {
  kinds: DeviceKind[];
  protocols: Record<string, string>;
}
