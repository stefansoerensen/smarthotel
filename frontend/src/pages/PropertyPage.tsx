import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";
import DeviceRow from "../components/DeviceRow";
import Field, { buttonClass, inputClass } from "../components/Field";
import { useAuthStore } from "../hooks/useAuthStore";
import { getCatalogue, listDevices, patchDevice, registerDevice, retireDevice } from "../services/devices";
import { getProperty, patchProperty } from "../services/estate";
import type { ApiError, Catalogue, Device, DevicePatch, Property } from "../types";
import { suggestDeviceCode } from "../utils/codes";

// ``code`` is null while it follows the suggestion and holds the user's text once they edit it.
// The name is always "<Art> <Ort>"; the bus address comes with the import from the building (SB2).
const EMPTY: { code: string | null; kind: string; protocol: string; location: string } = {
  code: null,
  kind: "",
  protocol: "",
  location: "",
};


export default function PropertyPage() {
  const { code = "" } = useParams();
  const [property, setProperty] = useState<Property | null>(null);
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [kindFilter, setKindFilter] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const [propertyDraft, setPropertyDraft] = useState<{
    name: string;
    street: string;
    postal_code: string;
    city: string;
  } | null>(null);

  const loadDevices = useCallback(async () => {
    setDevices((await listDevices(code, kindFilter || undefined)).items);
  }, [code, kindFilter]);

  useEffect(() => {
    Promise.all([getProperty(code), getCatalogue()])
      .then(([p, c]) => {
        setProperty(p);
        setCatalogue(c);
        setForm((f) => ({
          ...f,
          kind: f.kind || c.kinds[0]?.kind || "",
          protocol: f.protocol || Object.keys(c.protocols)[0] || "",
        }));
      })
      .catch((err: ApiError) => setError(err.message));
  }, [code]);

  useEffect(() => {
    loadDevices().catch((err: ApiError) => setError(err.message));
  }, [loadDevices]);

  const labelOf = (kind: string) => catalogue?.kinds.find((k) => k.kind === kind)?.label ?? kind;
  const deviceName = form.location.trim() ? `${labelOf(form.kind)} ${form.location.trim()}` : "";
  const deviceCode =
    form.code ??
    suggestDeviceCode({
      location: form.location,
      kind: form.kind,
      name: deviceName,
      taken: devices.map((d) => d.code),
    });
  const selectedIsSafety = catalogue?.kinds.find((k) => k.kind === form.kind)?.safety ?? false;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await registerDevice(code, {
        code: deviceCode,
        name: deviceName,
        kind: form.kind,
        protocol: form.protocol,
        location: form.location.trim(),
      });
      setForm((f) => ({ ...EMPTY, kind: f.kind, protocol: f.protocol }));
      await loadDevices();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError((err as ApiError).message);
      throw err;
    }
  }

  const saveDevice = (deviceCode: string) => (changes: DevicePatch) =>
    run(async () => {
      await patchDevice(code, deviceCode, changes);
      await loadDevices();
    });

  const retire = (deviceCode: string) => () =>
    run(async () => {
      await retireDevice(code, deviceCode);
      await loadDevices();
    });

  function editProperty() {
    if (property) {
      setPropertyDraft({
        name: property.name,
        street: property.street ?? "",
        postal_code: property.postal_code ?? "",
        city: property.city ?? "",
      });
    }
  }

  async function saveProperty(event: FormEvent) {
    event.preventDefault();
    if (!propertyDraft) {
      return;
    }
    await run(async () => {
      const updated = await patchProperty(code, {
        name: propertyDraft.name.trim(),
        street: propertyDraft.street.trim() || null,
        postal_code: propertyDraft.postal_code.trim() || null,
        city: propertyDraft.city.trim() || null,
      });
      setProperty(updated);
      setPropertyDraft(null);
    }).catch(() => undefined);
  }

  return (
    <section className="flex flex-col gap-6">
      {propertyDraft ? (
        <form
          aria-label="Haus bearbeiten"
          onSubmit={saveProperty}
          className="grid grid-cols-4 items-end gap-3 rounded-lg bg-white p-4 shadow-sm"
        >
          <Field label="Name">
            <input className={inputClass} value={propertyDraft.name} onChange={(e) => setPropertyDraft({ ...propertyDraft, name: e.target.value })} />
          </Field>
          <Field label="Straße">
            <input className={inputClass} value={propertyDraft.street} onChange={(e) => setPropertyDraft({ ...propertyDraft, street: e.target.value })} />
          </Field>
          <Field label="PLZ">
            <input className={inputClass} value={propertyDraft.postal_code} onChange={(e) => setPropertyDraft({ ...propertyDraft, postal_code: e.target.value })} />
          </Field>
          <Field label="Stadt">
            <input className={inputClass} value={propertyDraft.city} onChange={(e) => setPropertyDraft({ ...propertyDraft, city: e.target.value })} />
          </Field>
          <p className="col-span-2 text-xs text-ink/60">Code {code} bleibt; er steht in Links und Ereignissen.</p>
          <button type="button" className="rounded px-3 py-1.5 text-sm hover:bg-burgundy-light" onClick={() => setPropertyDraft(null)}>
            Abbrechen
          </button>
          <button type="submit" className={buttonClass} disabled={!propertyDraft.name.trim()}>
            Speichern
          </button>
        </form>
      ) : (
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">{property?.name ?? code}</h1>
            <p className="text-ink/60">
              {code}
              {property ? ` · ${property.tenant_code} · ${property.time_zone}` : ""}
              {property?.street || property?.city
                ? ` · ${[property.street, [property.postal_code, property.city].filter(Boolean).join(" ")].filter(Boolean).join(", ")}`
                : ""}
            </p>
          </div>
          {isAdmin && property && (
            <button type="button" className="rounded px-3 py-1.5 text-sm text-burgundy hover:bg-burgundy-light" onClick={editProperty}>
              Haus bearbeiten
            </button>
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Geräteregister</h2>
        <label className="flex items-center gap-2 text-xs text-ink/70">
          Art
          <select className={inputClass} value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
            <option value="">alle</option>
            {catalogue?.kinds.map((k) => (
              <option key={k.kind} value={k.kind}>
                {k.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <table className="w-full overflow-hidden rounded-lg bg-white text-left shadow-sm">
        <thead className="bg-burgundy-light text-xs text-ink/70">
          <tr>
            <th className="p-2">Ort</th>
            <th className="p-2">Code</th>
            <th className="p-2">Name</th>
            <th className="p-2">Art</th>
            <th className="p-2">Protokoll</th>
            <th className="p-2">Steuerung</th>
            <th className="p-2">
              <span className="sr-only">Aktionen</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink/10">
          {devices.length === 0 && (
            <tr>
              <td colSpan={7} className="p-4 text-ink/60">
                Keine Geräte.
              </td>
            </tr>
          )}
          {devices.map((d) => (
            <DeviceRow
              key={d.code}
              device={d}
              catalogue={catalogue}
              onSave={saveDevice(d.code)}
              onRetire={retire(d.code)}
            />
          ))}
        </tbody>
      </table>

      <form onSubmit={submit} className="grid grid-cols-3 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
        <Field label="Art">
          <select className={inputClass} value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            {catalogue?.kinds.map((k) => (
              <option key={k.kind} value={k.kind}>
                {k.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Ort">
          <input
            className={inputClass}
            value={form.location}
            placeholder="Zimmernummer, Flur o. ä."
            onChange={(e) => setForm({ ...form, location: e.target.value })}
          />
        </Field>
        <Field label="Protokoll">
          <select className={inputClass} value={form.protocol} onChange={(e) => setForm({ ...form, protocol: e.target.value })}>
            {catalogue &&
              Object.entries(catalogue.protocols).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
          </select>
        </Field>
        <Field label="Code">
          <input className={inputClass} value={deviceCode} onChange={(e) => setForm({ ...form, code: e.target.value || null })} />
        </Field>
        <p className="text-xs text-ink/60">
          {deviceName ? <span className="block font-medium text-ink">{deviceName}</span> : null}
          {selectedIsSafety ? "Sicherheitsgerät: wird nur gelesen, nie gesteuert." : ""}
        </p>
        <button type="submit" className={buttonClass} disabled={!deviceCode || !deviceName}>
          Gerät anlegen
        </button>
      </form>
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </section>
  );
}
