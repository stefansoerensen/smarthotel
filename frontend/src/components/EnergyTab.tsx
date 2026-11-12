import { useCallback, useEffect, useState } from "react";
import { getNights, getSeries } from "../services/energy";
import type { ApiError, EnergyNights, EnergySeries } from "../types";

interface EnergyTabProps {
  propertyCode: string;
  /** Today as YYYY-MM-DD; injectable for tests. */
  today?: string;
}

const kwh = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const day = new Intl.DateTimeFormat("de-DE", { weekday: "short", day: "2-digit", month: "2-digit", timeZone: "UTC" });

function shift(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function localToday(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function euro(value: string | null): string {
  return value === null ? "–" : `${value.replace(".", ",")} €`;
}

/** Energy per day and per occupied night — the building's input to the live P&L (d31). */
export default function EnergyTab({ propertyCode, today = localToday() }: EnergyTabProps) {
  const [days, setDays] = useState(7);
  const [series, setSeries] = useState<EnergySeries | null>(null);
  const [nights, setNights] = useState<EnergyNights | null>(null);
  const [error, setError] = useState<string | null>(null);

  const from = shift(today, -(days - 1));

  const load = useCallback(async () => {
    const [s, n] = await Promise.all([
      getSeries(propertyCode, from, today, "day"),
      getNights(propertyCode, from, shift(today, -1)),
    ]);
    setSeries(s);
    setNights(n);
  }, [propertyCode, from, today]);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  const max = Math.max(0.001, ...(series?.buckets.map((b) => b.kwh) ?? [0]));
  const summary = nights?.summary;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex gap-2">
        {[7, 30].map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={days === n}
            className={`rounded px-3 py-1.5 text-sm ${days === n ? "bg-burgundy text-white" : "bg-white hover:bg-burgundy-light"}`}
            onClick={() => setDays(n)}
          >
            {n} Tage
          </button>
        ))}
      </div>

      {series && summary && (
        <ul aria-label="Kennzahlen" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <li className="rounded-lg bg-white p-3 shadow-sm">
            <p className="text-xs text-ink/60">Verbrauch gesamt</p>
            <p className="text-xl font-semibold">{`${kwh.format(series.total_kwh)} kWh`}</p>
          </li>
          <li className="rounded-lg bg-white p-3 shadow-sm">
            <p className="text-xs text-ink/60">Belegte Nächte</p>
            <p className="text-xl font-semibold">{summary.occupied_nights}</p>
          </li>
          <li className="rounded-lg bg-white p-3 shadow-sm">
            <p className="text-xs text-ink/60">je belegter Nacht</p>
            <p className="text-xl font-semibold">
              {summary.kwh_per_occupied_night === null ? "–" : `${kwh.format(summary.kwh_per_occupied_night)} kWh`}
            </p>
          </li>
          <li className="rounded-lg bg-white p-3 shadow-sm">
            <p className="text-xs text-ink/60">Kosten je belegter Nacht</p>
            <p className="text-xl font-semibold">{euro(summary.cost_per_occupied_night_eur)}</p>
            {summary.price_eur_per_kwh === null && <p className="text-xs text-ink/50">Preis je kWh im Tab Hotel OS hinterlegen</p>}
          </li>
        </ul>
      )}

      {series && (
        <section className="rounded-lg bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold">Verbrauch je Tag</h2>
          <ul aria-label="Verbrauch je Tag" className="flex h-40 items-end gap-1">
            {series.buckets.map((b) => (
              <li key={b.start} className="flex flex-1 flex-col items-center gap-1" title={`${kwh.format(b.kwh)} kWh`}>
                <span className="text-[10px] text-ink/60">{b.kwh ? kwh.format(b.kwh) : ""}</span>
                <span className="w-full rounded-t bg-burgundy" style={{ height: `${Math.round((b.kwh / max) * 100)}px` }} />
                <span className="text-[10px] text-ink/50">{day.format(new Date(new Date(b.start).getTime() + 12 * 3600_000))}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {nights && nights.nights.length > 0 && (
        <table aria-label="Nächte" className="w-full overflow-hidden rounded-lg bg-white text-left shadow-sm">
          <thead className="bg-burgundy-light text-xs text-ink/70">
            <tr>
              <th className="p-2">Nacht</th>
              <th className="p-2">Zimmer</th>
              <th className="p-2">Belegt</th>
              <th className="p-2">Reservierung</th>
              <th className="p-2 text-right">kWh</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/10">
            {nights.nights
              .filter((n) => n.occupied || n.kwh > 0)
              .map((n) => (
                <tr key={`${n.date}-${n.room_code}`}>
                  <td className="p-2">{day.format(new Date(`${n.date}T12:00:00Z`))}</td>
                  <td className="p-2">{n.room_code}</td>
                  <td className="p-2">{n.occupied ? "ja" : "nein"}</td>
                  <td className="p-2 font-mono text-xs">{n.reservation_code ?? "–"}</td>
                  <td className="p-2 text-right">{kwh.format(n.kwh)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      )}
      <p className="text-xs text-ink/50">
        Nacht = 12:00 bis 12:00 Ortszeit; belegt, wenn laut Hotel OS ein Gast um Mitternacht im Zimmer war. Grundlage sind die Wärmezähler der
        Zimmer.
      </p>
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </div>
  );
}
