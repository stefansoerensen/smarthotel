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
  /** False for sensors and safety devices: the platform never sets them. */
  writable: boolean;
}

export interface Catalogue {
  kinds: DeviceKind[];
  protocols: Record<string, string>;
}

export interface TemplatePoint {
  key: string;
  label: string;
  kind: string;
  protocol: string;
  unit: string | null;
  writable: boolean;
}

export interface RoomType {
  code: string;
  name: string;
  description: string | null;
  points: TemplatePoint[];
}

export interface RoomTypeInput {
  code: string;
  name: string;
  standard_points: boolean;
}

export interface PointInput {
  key: string;
  label: string;
  kind: string;
  protocol: string;
  unit?: string;
  writable: boolean;
}

export interface RolloutInput {
  room_type_code: string;
  room_codes: string[];
  floor?: string;
}

export interface RolloutResult {
  rooms_created: number;
  rooms_unchanged: number;
  devices_created: number;
  conflicts: string[];
}

export interface RoomPoint {
  key: string;
  label: string;
  kind: string;
  unit: string | null;
  writable: boolean;
  device_code: string | null;
  value: number | null;
  value_at: string | null;
  source: string | null;
}

export interface Room {
  code: string;
  name: string;
  floor: string | null;
  room_type_code: string | null;
  points: RoomPoint[];
}

export interface SimulatorRoomInput {
  window?: boolean;
  presence?: boolean;
}
