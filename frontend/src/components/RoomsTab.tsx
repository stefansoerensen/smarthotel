import { useCallback, useEffect, useState } from "react";
import { listRooms, simulateRoom, simulateStep, writePoint } from "../services/twin";
import type { ApiError, Room } from "../types";
import RoomTile from "./RoomTile";
import { inputClass } from "./Field";

interface RoomsTabProps {
  propertyCode: string;
}

const stepButton = "rounded border border-burgundy px-3 py-1.5 text-sm text-burgundy hover:bg-burgundy-light disabled:opacity-50";

/** The digital twin of every room, with simulator controls. */
export default function RoomsTab({ propertyCode }: RoomsTabProps) {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [outdoor, setOutdoor] = useState("5");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRooms((await listRooms(propertyCode)).items);
    setLoaded(true);
  }, [propertyCode]);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  function replaceRoom(updated: Room) {
    setRooms((all) => all.map((r) => (r.code === updated.code ? updated : r)));
  }

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError((err as ApiError).message);
      throw err;
    }
  }

  async function advance(minutes: number) {
    setBusy(true);
    await run(async () => {
      await simulateStep(propertyCode, minutes, Number(outdoor.replace(",", ".")) || 0);
      await load();
    })
      .catch(() => undefined)
      .finally(() => setBusy(false));
  }

  if (loaded && rooms.length === 0) {
    return (
      <p className="rounded-lg bg-white p-4 text-ink/60 shadow-sm">
        Noch keine Zimmer. Unter „Raumtypen“ einen Raumtyp anlegen und auf Zimmer ausrollen.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg bg-white p-3 shadow-sm">
        <span className="text-xs font-medium text-ink/70">Simulator</span>
        <label className="flex items-center gap-2 text-xs text-ink/70">
          Außen °C
          <input className={`${inputClass} w-16`} value={outdoor} onChange={(e) => setOutdoor(e.target.value)} />
        </label>
        <button type="button" className={stepButton} disabled={busy} onClick={() => void advance(15)}>
          +15 min
        </button>
        <button type="button" className={stepButton} disabled={busy} onClick={() => void advance(60)}>
          +1 h
        </button>
        <span className="ml-auto text-xs text-ink/50">{rooms.length} Zimmer</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {rooms.map((room) => (
          <RoomTile
            key={room.code}
            room={room}
            onSetpoint={(value) => run(async () => replaceRoom(await writePoint(propertyCode, room.code, "setpoint", value)))}
            onSimulate={(input) => run(async () => replaceRoom(await simulateRoom(propertyCode, room.code, input)))}
          />
        ))}
      </div>
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </div>
  );
}
