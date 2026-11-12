import type {
  Page,
  PointInput,
  RolloutInput,
  RolloutResult,
  Room,
  RoomType,
  RoomTypeInput,
  SimulatorRoomInput,
} from "../types";
import { api } from "./api";

const base = (propertyCode: string) => `/properties/${encodeURIComponent(propertyCode)}`;

export async function listRoomTypes(propertyCode: string): Promise<Page<RoomType>> {
  return (await api.get<Page<RoomType>>(`${base(propertyCode)}/room-types`)).data;
}

export async function createRoomType(propertyCode: string, input: RoomTypeInput): Promise<RoomType> {
  return (await api.post<RoomType>(`${base(propertyCode)}/room-types`, input)).data;
}

export async function addPoint(propertyCode: string, typeCode: string, input: PointInput): Promise<RoomType> {
  const url = `${base(propertyCode)}/room-types/${encodeURIComponent(typeCode)}/points`;
  return (await api.post<RoomType>(url, input)).data;
}

export async function removePoint(propertyCode: string, typeCode: string, key: string): Promise<RoomType> {
  const url = `${base(propertyCode)}/room-types/${encodeURIComponent(typeCode)}/points/${encodeURIComponent(key)}`;
  return (await api.delete<RoomType>(url)).data;
}

export async function rollout(propertyCode: string, input: RolloutInput): Promise<RolloutResult> {
  return (await api.post<RolloutResult>(`${base(propertyCode)}/rollout`, input)).data;
}

export async function listRooms(propertyCode: string): Promise<Page<Room>> {
  return (await api.get<Page<Room>>(`${base(propertyCode)}/rooms`)).data;
}

export async function writePoint(propertyCode: string, roomCode: string, key: string, value: number): Promise<Room> {
  const url = `${base(propertyCode)}/rooms/${encodeURIComponent(roomCode)}/points/${encodeURIComponent(key)}`;
  return (await api.put<Room>(url, { value })).data;
}

export async function simulateStep(
  propertyCode: string,
  minutes: number,
  outdoor: number,
): Promise<{ rooms: number }> {
  return (await api.post<{ rooms: number }>(`${base(propertyCode)}/simulator/step`, { minutes, outdoor })).data;
}

export async function simulateRoom(propertyCode: string, roomCode: string, input: SimulatorRoomInput): Promise<Room> {
  const url = `${base(propertyCode)}/simulator/rooms/${encodeURIComponent(roomCode)}`;
  return (await api.post<Room>(url, input)).data;
}
