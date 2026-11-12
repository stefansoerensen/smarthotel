import { DoorOpen, Minus, Plus, User } from "lucide-react";
import type { Room, SimulatorRoomInput } from "../types";

interface RoomTileProps {
  room: Room;
  onSetpoint: (value: number) => Promise<void>;
  onSimulate: (input: SimulatorRoomInput) => Promise<void>;
}

const de1 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const de2 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 });

function valueOf(room: Room, key: string): number | null {
  return room.points.find((p) => p.key === key)?.value ?? null;
}

function has(room: Room, key: string): boolean {
  return room.points.some((p) => p.key === key);
}

const chip = "inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs";

/** One room of the twin: temperature, set point, window, presence, valve, heat meter. */
export default function RoomTile({ room, onSetpoint, onSimulate }: RoomTileProps) {
  const temperature = valueOf(room, "temperature");
  const setpoint = valueOf(room, "setpoint") ?? 21;
  const windowOpen = (valueOf(room, "window") ?? 0) >= 0.5;
  const present = (valueOf(room, "presence") ?? 0) >= 0.5;
  const valve = valueOf(room, "valve");
  const meter = valueOf(room, "heat_meter");
  const cold = temperature !== null && temperature < setpoint - 1;

  return (
    <article aria-label={`Zimmer ${room.code}`} className="flex flex-col gap-2 rounded-lg bg-white p-3 shadow-sm">
      <header className="flex items-baseline justify-between">
        <span className="font-semibold">{room.code}</span>
        <span className="text-xs text-ink/50">{room.room_type_code ?? ""}</span>
      </header>
      {has(room, "temperature") && (
        <p className={`text-2xl font-semibold ${cold ? "text-burgundy" : ""}`}>
          {temperature === null ? "–" : `${de1.format(temperature)} °C`}
        </p>
      )}
      {has(room, "setpoint") && (
        <div className="flex items-center gap-1 text-xs text-ink/70">
          <button
            type="button"
            aria-label="Sollwert senken"
            className="rounded p-1 hover:bg-burgundy-light"
            onClick={() => void onSetpoint(setpoint - 0.5).catch(() => undefined)}
          >
            <Minus size={12} aria-hidden />
          </button>
          <span>Soll {de1.format(setpoint)} °C</span>
          <button
            type="button"
            aria-label="Sollwert erhöhen"
            className="rounded p-1 hover:bg-burgundy-light"
            onClick={() => void onSetpoint(setpoint + 0.5).catch(() => undefined)}
          >
            <Plus size={12} aria-hidden />
          </button>
        </div>
      )}
      <div className="flex flex-wrap gap-1">
        {has(room, "window") && (
          <button
            type="button"
            className={`${chip} ${windowOpen ? "bg-burgundy text-white" : "bg-bone"}`}
            onClick={() => void onSimulate({ window: !windowOpen }).catch(() => undefined)}
          >
            <DoorOpen size={12} aria-hidden />
            {windowOpen ? "Fenster offen" : "Fenster zu"}
          </button>
        )}
        {has(room, "presence") && (
          <button
            type="button"
            className={`${chip} ${present ? "bg-ink text-white" : "bg-bone"}`}
            onClick={() => void onSimulate({ presence: !present }).catch(() => undefined)}
          >
            <User size={12} aria-hidden />
            {present ? "belegt" : "frei"}
          </button>
        )}
      </div>
      <p className="flex justify-between text-xs text-ink/60">
        {has(room, "valve") && <span>{`Ventil ${valve === null ? "–" : Math.round(valve)} %`}</span>}
        {has(room, "heat_meter") && <span>{meter === null ? "–" : `${de2.format(meter)} kWh`}</span>}
      </p>
    </article>
  );
}
