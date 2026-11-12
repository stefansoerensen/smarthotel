import { Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { listGateways } from "../services/devices";
import { addPoint, createRoomType, listRoomTypes, removePoint, rollout } from "../services/twin";
import type { ApiError, Catalogue, Gateway, RoomType } from "../types";
import { suggestCode } from "../utils/codes";
import { parseRoomCodes } from "../utils/rooms";
import Field, { buttonClass, inputClass } from "./Field";

interface RoomTypesTabProps {
  propertyCode: string;
  catalogue: Catalogue | null;
  onRolledOut?: () => void;
}

/** Turn a label into a point key: lower case, ASCII, underscores. */
function keyOf(label: string): string {
  return suggestCode(label, { maxLength: 40 }).toLowerCase().replace(/-/g, "_");
}

interface PointFormProps {
  catalogue: Catalogue | null;
  onAdd: (label: string, kind: string, protocol: string) => Promise<void>;
  onCancel: () => void;
}

function PointForm({ catalogue, onAdd, onCancel }: PointFormProps) {
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState(catalogue?.kinds[0]?.kind ?? "");
  const [protocol, setProtocol] = useState(Object.keys(catalogue?.protocols ?? {})[0] ?? "knx");
  return (
    <div className="flex flex-wrap items-end gap-2 border-t border-ink/10 pt-3">
      <Field label="Bezeichnung">
        <input className={inputClass} value={label} onChange={(e) => setLabel(e.target.value)} />
      </Field>
      <Field label="Art">
        <select className={inputClass} value={kind} onChange={(e) => setKind(e.target.value)}>
          {catalogue?.kinds.map((k) => (
            <option key={k.kind} value={k.kind}>
              {k.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Protokoll">
        <select className={inputClass} value={protocol} onChange={(e) => setProtocol(e.target.value)}>
          {catalogue &&
            Object.entries(catalogue.protocols).map(([key, text]) => (
              <option key={key} value={key}>
                {text}
              </option>
            ))}
        </select>
      </Field>
      <button
        type="button"
        className={buttonClass}
        disabled={!label.trim() || !keyOf(label)}
        onClick={() => void onAdd(label.trim(), kind, protocol).catch(() => undefined)}
      >
        Hinzufügen
      </button>
      <button type="button" className="rounded px-2 py-1.5 text-sm hover:bg-burgundy-light" onClick={onCancel}>
        Abbrechen
      </button>
    </div>
  );
}

/** Room types (templates), their data points and the rollout to many rooms. */
export default function RoomTypesTab({ propertyCode, catalogue, onRolledOut }: RoomTypesTabProps) {
  const [types, setTypes] = useState<RoomType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [create, setCreate] = useState<{ name: string; code: string | null; standard: boolean }>({
    name: "",
    code: null,
    standard: true,
  });
  const [addingTo, setAddingTo] = useState<string | null>(null);
  const [plan, setPlan] = useState({ type: "", rooms: "", floor: "", gateway: "" });
  const [gateways, setGateways] = useState<Gateway[]>([]);

  const load = useCallback(async () => {
    const [page, gws] = await Promise.all([listRoomTypes(propertyCode), listGateways(propertyCode)]);
    setGateways(gws.items);
    setTypes(page.items);
    setPlan((p) => ({ ...p, type: p.type || page.items[0]?.code || "" }));
  }, [propertyCode]);

  useEffect(() => {
    load().catch((err: ApiError) => setError(err.message));
  }, [load]);

  async function run(action: () => Promise<void>) {
    setError(null);
    setStatus(null);
    try {
      await action();
    } catch (err) {
      setError((err as ApiError).message);
      throw err;
    }
  }

  const typeCode = create.code ?? suggestCode(create.name, { maxLength: 20, taken: types.map((t) => t.code) });
  const parsed = parseRoomCodes(plan.rooms);
  const labelOf = (kind: string) => catalogue?.kinds.find((k) => k.kind === kind)?.label ?? kind;

  async function submitType(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const created = await createRoomType(propertyCode, {
        code: typeCode,
        name: create.name.trim(),
        standard_points: create.standard,
      });
      setCreate({ name: "", code: null, standard: true });
      setPlan((p) => ({ ...p, type: p.type || created.code }));
      await load();
    }).catch(() => undefined);
  }

  async function submitRollout(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const result = await rollout(propertyCode, {
        room_type_code: plan.type,
        room_codes: parsed.codes,
        floor: plan.floor.trim() || undefined,
        ...(plan.gateway ? { gateway_code: plan.gateway } : {}),
      });
      const parts = [`${result.rooms_created} Zimmer angelegt, ${result.devices_created} Geräte registriert`];
      if (result.rooms_unchanged) {
        parts.push(`${result.rooms_unchanged} unverändert`);
      }
      if (result.conflicts.length) {
        parts.push(`anderer Raumtyp, nicht geändert: ${result.conflicts.join(", ")}`);
      }
      setStatus(parts.join(" · "));
      setPlan((p) => ({ ...p, rooms: "" }));
      onRolledOut?.();
    }).catch(() => undefined);
  }

  return (
    <div className="flex flex-col gap-6">
      {types.map((t) => (
        <section key={t.code} aria-label={`Raumtyp ${t.code}`} className="flex flex-col gap-3 rounded-lg bg-white p-4 shadow-sm">
          <header className="flex items-baseline justify-between">
            <h3 className="font-semibold">
              {t.name} <span className="font-mono text-xs text-ink/50">{t.code}</span>
            </h3>
            <span className="text-xs text-ink/50">{t.points.length} Datenpunkte</span>
          </header>
          <ul className="flex flex-wrap gap-2">
            {t.points.map((p) => (
              <li key={p.key} className="inline-flex items-center gap-1 rounded bg-bone px-2 py-1 text-xs">
                <span className="font-medium">{p.label}</span>
                <span className="text-ink/50">
                  {labelOf(p.kind)} · {p.protocol}
                  {p.unit ? ` · ${p.unit}` : ""} · {p.writable ? "stellbar" : "nur lesen"}
                </span>
                <button
                  type="button"
                  aria-label={`${p.label} entfernen`}
                  className="rounded p-0.5 hover:bg-burgundy-light"
                  onClick={() =>
                    void run(async () => {
                      await removePoint(propertyCode, t.code, p.key);
                      await load();
                    }).catch(() => undefined)
                  }
                >
                  <X size={12} aria-hidden />
                </button>
              </li>
            ))}
          </ul>
          {addingTo === t.code ? (
            <PointForm
              catalogue={catalogue}
              onCancel={() => setAddingTo(null)}
              onAdd={(label, kind, protocol) =>
                run(async () => {
                  const writable = catalogue?.kinds.find((k) => k.kind === kind)?.writable ?? false;
                  await addPoint(propertyCode, t.code, { key: keyOf(label), label, kind, protocol, writable });
                  setAddingTo(null);
                  await load();
                })
              }
            />
          ) : (
            <button
              type="button"
              className="inline-flex w-fit items-center gap-1 rounded px-2 py-1 text-xs text-burgundy hover:bg-burgundy-light"
              onClick={() => setAddingTo(t.code)}
            >
              <Plus size={12} aria-hidden /> Datenpunkt hinzufügen
            </button>
          )}
        </section>
      ))}

      <form aria-label="Raumtyp anlegen" onSubmit={submitType} className="grid grid-cols-4 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
        <Field label="Name">
          <input className={inputClass} value={create.name} placeholder="z. B. Standardzimmer" onChange={(e) => setCreate({ ...create, name: e.target.value })} />
        </Field>
        <Field label="Code">
          <input className={inputClass} value={typeCode} onChange={(e) => setCreate({ ...create, code: e.target.value || null })} />
        </Field>
        <label className="flex items-center gap-2 text-xs text-ink/70">
          <input type="checkbox" checked={create.standard} onChange={(e) => setCreate({ ...create, standard: e.target.checked })} />
          Standard-Datenpunkte
        </label>
        <button type="submit" className={buttonClass} disabled={!create.name.trim() || !typeCode}>
          Raumtyp anlegen
        </button>
      </form>

      {types.length > 0 && (
        <form aria-label="Ausrollen" onSubmit={submitRollout} className="grid grid-cols-5 items-end gap-3 rounded-lg bg-white p-4 shadow-sm">
          <Field label="Raumtyp">
            <select className={inputClass} value={plan.type} onChange={(e) => setPlan({ ...plan, type: e.target.value })}>
              {types.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Zimmer">
            <input className={inputClass} value={plan.rooms} placeholder="101-120, 201-210" onChange={(e) => setPlan({ ...plan, rooms: e.target.value })} />
          </Field>
          <Field label="Etage">
            <input className={inputClass} value={plan.floor} placeholder="optional" onChange={(e) => setPlan({ ...plan, floor: e.target.value })} />
          </Field>
          {gateways.length > 0 ? (
            <Field label="Gateway">
              <select className={inputClass} value={plan.gateway} onChange={(e) => setPlan({ ...plan, gateway: e.target.value })}>
                <option value="">ohne (Cloud-Simulator)</option>
                {gateways.map((g) => (
                  <option key={g.code} value={g.code}>
                    {g.code} – {g.name}
                  </option>
                ))}
              </select>
            </Field>
          ) : (
            <span />
          )}
          <button type="submit" className={buttonClass} disabled={!plan.type || parsed.codes.length === 0 || parsed.error !== null}>
            Ausrollen
          </button>
          <p className="col-span-5 text-xs text-ink/60">
            {parsed.error ?? (parsed.codes.length ? `${parsed.codes.length} Zimmer` : "Zimmer als Liste oder Bereiche, z. B. 101-120, 201-210")}
          </p>
        </form>
      )}

      {status && (
        <p role="status" className="text-sm">
          {status}
        </p>
      )}
      {error && (
        <p role="alert" className="text-burgundy">
          {error}
        </p>
      )}
    </div>
  );
}
