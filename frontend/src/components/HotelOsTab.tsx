import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { getLink, listFaults, saveLink, sync } from "../services/hotelOs";
import type { ApiError, Fault, HotelOsLink } from "../types";
import Field, { buttonClass, inputClass } from "./Field";

interface HotelOsTabProps {
  propertyCode: string;
}

const SEVERITY: Record<Fault["severity"], string> = { Blocker: "blockiert", Today: "heute", Attention: "beachten" };
const time = new Intl.DateTimeFormat("de-DE", { dateStyle: "short", timeStyle: "short" });

/** Coupling with the Hotel OS: link, sync and the faults the front desk sees (ADR-0007). */
export default function HotelOsTab({ propertyCode }: HotelOsTabProps) {
  const [link, setLink] = useState<HotelOsLink | null>(null);
  const [draft, setDraft] = useState({ code: "", comfort: "21", eco: "17", enabled: true });
  const [faults, setFaults] = useState<Fault[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [l, f] = await Promise.all([getLink(propertyCode), listFaults(propertyCode)]);
    setLink(l);
    setFaults(f.items);
    setDraft({
      code: l.hotel_os_property_code ?? "",
      comfort: String(l.comfort_setpoint),
      eco: String(l.eco_setpoint),
      enabled: l.hotel_os_property_code ? l.enabled : true,
    });
  }, [propertyCode]);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setLink(
        await saveLink(propertyCode, {
          hotel_os_property_code: draft.code.trim(),
          enabled: draft.enabled,
          comfort_setpoint: Number(draft.comfort.replace(",", ".")),
          eco_setpoint: Number(draft.eco.replace(",", ".")),
        }),
      );
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function runSync() {
    setError(null);
    setStatus(null);
    setBusy(true);
    try {
      const result = await sync(propertyCode);
      const parts = [`${result.rooms_changed} Zimmer geändert`];
      if (result.unmatched_units.length) {
        parts.push(`ohne Zimmer im Haus: ${result.unmatched_units.join(", ")}`);
      }
      setStatus(parts.join(" · "));
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {link && !link.configured && (
        <p className="rounded-lg border border-burgundy bg-white p-3 text-sm">
          Die Verbindung zum Hotel OS ist nicht eingerichtet: HOTEL_OS_URL, HOTEL_OS_USERNAME und HOTEL_OS_PASSWORD fehlen in
          Railway. Die Verknüpfung lässt sich trotzdem schon speichern.
        </p>
      )}
      <form aria-label="Verknüpfung" onSubmit={save} className="grid grid-cols-5 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
        <Field label="Hauscode im Hotel OS">
          <input className={inputClass} value={draft.code} onChange={(e) => setDraft({ ...draft, code: e.target.value })} />
        </Field>
        <Field label="Komfort °C">
          <input className={inputClass} value={draft.comfort} onChange={(e) => setDraft({ ...draft, comfort: e.target.value })} />
        </Field>
        <Field label="Eco °C">
          <input className={inputClass} value={draft.eco} onChange={(e) => setDraft({ ...draft, eco: e.target.value })} />
        </Field>
        <label className="flex items-center gap-2 text-xs text-ink/70">
          <input type="checkbox" checked={draft.enabled} onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })} />
          aktiv
        </label>
        <button type="submit" className={buttonClass} disabled={!draft.code.trim()}>
          Speichern
        </button>
        <p className="col-span-5 text-xs text-ink/60">
          Belegt → Komfort, Anreise heute → Vorheizen auf Komfort, frei → Eco. Zimmer und Einheiten im Hotel OS werden über den Namen
          zugeordnet (101 = 101). Der Sollwert wird nur beim Wechsel gesetzt; was der Gast verstellt, bleibt bis zum nächsten Wechsel.
        </p>
      </form>

      {link?.hotel_os_property_code && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg bg-white p-3 shadow-sm">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded border border-burgundy px-3 py-1.5 text-sm text-burgundy hover:bg-burgundy-light disabled:opacity-50"
            disabled={busy || !link.enabled}
            onClick={() => void runSync()}
          >
            <RefreshCw size={14} aria-hidden /> Jetzt abgleichen
          </button>
          <span className="text-xs text-ink/60">
            {link.last_sync_at ? `Letzter Abgleich ${time.format(new Date(link.last_sync_at))}` : "Noch kein Abgleich"}
            {link.last_sync_error ? ` · Fehler: ${link.last_sync_error}` : ""}
          </span>
        </div>
      )}
      {status && (
        <p role="status" className="text-sm">
          {status}
        </p>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">Störungen für die Rezeption</h2>
        {faults.length === 0 ? (
          <p className="text-ink/60">Keine Störungen.</p>
        ) : (
          <ul aria-label="Störungen" className="divide-y divide-ink/10 rounded-lg bg-white shadow-sm">
            {faults.map((f, i) => (
              <li key={`${f.kind}-${f.unit_name ?? ""}-${i}`} className="flex items-center gap-3 p-3">
                <span className={`rounded px-2 py-0.5 text-xs ${f.severity === "Attention" ? "bg-bone" : "bg-burgundy text-white"}`}>
                  {SEVERITY[f.severity]}
                </span>
                <span className="flex-1">{f.message}</span>
                <span className="text-xs text-ink/50">{f.since ? time.format(new Date(f.since)) : ""}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </div>
  );
}
