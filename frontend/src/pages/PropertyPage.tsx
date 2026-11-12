import { ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";
import Field, { buttonClass, inputClass } from "../components/Field";
import { getCatalogue, listDevices, registerDevice } from "../services/devices";
import { getProperty } from "../services/estate";
import type { ApiError, Catalogue, Device, Property } from "../types";

const EMPTY = { code: "", name: "", kind: "", protocol: "", location: "", address: "" };

export default function PropertyPage() {
  const { code = "" } = useParams();
  const [property, setProperty] = useState<Property | null>(null);
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [kindFilter, setKindFilter] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);

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
  const selectedIsSafety = catalogue?.kinds.find((k) => k.kind === form.kind)?.safety ?? false;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await registerDevice(code, {
        code: form.code,
        name: form.name,
        kind: form.kind,
        protocol: form.protocol,
        location: form.location || undefined,
        address: form.address || undefined,
      });
      setForm((f) => ({ ...EMPTY, kind: f.kind, protocol: f.protocol }));
      await loadDevices();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">{property?.name ?? code}</h1>
        <p className="text-ink/60">
          {code}
          {property ? ` · ${property.tenant_code} · ${property.time_zone}` : ""}
        </p>
      </div>

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
            <th className="p-2">Adresse</th>
            <th className="p-2">Steuerung</th>
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
            <tr key={d.code}>
              <td className="p-2">{d.location ?? "–"}</td>
              <td className="p-2 font-mono text-xs">{d.code}</td>
              <td className="p-2">{d.name}</td>
              <td className="p-2">{labelOf(d.kind)}</td>
              <td className="p-2">{d.protocol}</td>
              <td className="p-2 font-mono text-xs">{d.address ?? "–"}</td>
              <td className="p-2">
                {d.safety ? (
                  <span className="inline-flex items-center gap-1 rounded bg-burgundy-light px-2 py-0.5 text-xs text-burgundy">
                    <ShieldAlert size={12} aria-hidden />
                    nur lesen
                  </span>
                ) : d.controllable ? (
                  <span className="text-xs">steuerbar</span>
                ) : (
                  <span className="text-xs text-ink/60">nur lesen</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={submit} className="grid grid-cols-4 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
        <Field label="Code">
          <input className={inputClass} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        </Field>
        <Field label="Name">
          <input className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Art">
          <select className={inputClass} value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            {catalogue?.kinds.map((k) => (
              <option key={k.kind} value={k.kind}>
                {k.label}
              </option>
            ))}
          </select>
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
        <Field label="Ort">
          <input className={inputClass} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        </Field>
        <Field label="Adresse">
          <input className={inputClass} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </Field>
        <p className="text-xs text-ink/60">
          {selectedIsSafety ? "Sicherheitsgerät: wird nur gelesen, nie gesteuert." : ""}
        </p>
        <button type="submit" className={buttonClass} disabled={!form.code || !form.name}>
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
