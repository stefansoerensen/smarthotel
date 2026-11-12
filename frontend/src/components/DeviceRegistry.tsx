import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { listDevices, patchDevice, registerDevice, retireDevice } from "../services/devices";
import type { ApiError, Catalogue, Device, DevicePatch } from "../types";
import { suggestDeviceCode } from "../utils/codes";
import DeviceRow from "./DeviceRow";
import Field, { buttonClass, inputClass } from "./Field";

// ``code`` is null while it follows the suggestion and holds the user's text once they edit it.
// The name is always "<Art> <Ort>"; the bus address comes with the import from the building (SB2).
const EMPTY: { code: string | null; kind: string; protocol: string; location: string } = {
  code: null,
  kind: "",
  protocol: "",
  location: "",
};

interface DeviceRegistryProps {
  propertyCode: string;
  catalogue: Catalogue | null;
}

/** The device registry of a property: list, filter, register, edit, retire. */
export default function DeviceRegistry({ propertyCode, catalogue }: DeviceRegistryProps) {
  const code = propertyCode;
  const [devices, setDevices] = useState<Device[]>([]);
  const [kindFilter, setKindFilter] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

  const loadDevices = useCallback(async () => {
    setDevices((await listDevices(code, kindFilter || undefined)).items);
  }, [code, kindFilter]);

  useEffect(() => {
    loadDevices().catch((err: ApiError) => setError(err.message));
  }, [loadDevices]);

  useEffect(() => {
    if (catalogue) {
      setForm((f) => ({
        ...f,
        kind: f.kind || catalogue.kinds[0]?.kind || "",
        protocol: f.protocol || Object.keys(catalogue.protocols)[0] || "",
      }));
    }
  }, [catalogue]);

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

  return (
    <div className="flex flex-col gap-6">
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
    </div>
  );
}
