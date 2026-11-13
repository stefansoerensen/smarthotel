import { useEffect, useState } from "react";
import { getOverview } from "../services/hotelOs";
import type { Overview } from "../types";

const one = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function Figure({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) {
  return (
    <li className="flex flex-col rounded-lg bg-white px-3 py-2 shadow-sm">
      <span className="text-[11px] text-ink/60">{label}</span>
      <span className={`text-sm font-semibold ${alert ? "text-burgundy" : ""}`}>{value}</span>
    </li>
  );
}

/** One line of figures for a property: rooms, comfort, faults, gateways, energy, commands. */
export default function OverviewBar({ propertyCode }: { propertyCode: string }) {
  const [data, setData] = useState<Overview | null>(null);

  useEffect(() => {
    getOverview(propertyCode)
      .then(setData)
      .catch(() => setData(null));
  }, [propertyCode]);

  if (!data) {
    return null;
  }
  const { rooms, faults, gateways } = data;
  return (
    <ul aria-label="Überblick" className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      <Figure label={`${rooms.total} Zimmer`} value={`${rooms.occupied} belegt · ${rooms.arriving} Anreise · ${rooms.vacant} frei`} />
      <Figure label="Ø belegte Zimmer" value={data.avg_temperature_occupied === null ? "–" : `${one.format(data.avg_temperature_occupied)} °C`} />
      <Figure label="Störungen" value={faults.total === 1 ? "1 Störung" : `${faults.total} Störungen`} alert={faults.blocker + faults.today > 0} />
      <Figure label="Gateways" value={`${gateways.online} / ${gateways.total} online`} alert={gateways.offline > 0} />
      <Figure label="Verbrauch gestern" value={`${one.format(data.kwh_yesterday)} kWh`} />
      <Figure label="Befehle" value={data.pending_commands === 1 ? "1 offener Befehl" : `${data.pending_commands} offene Befehle`} />
    </ul>
  );
}
