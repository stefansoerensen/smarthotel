import { Pencil, PowerOff, ShieldAlert } from "lucide-react";
import { useState } from "react";
import type { Catalogue, Device, DevicePatch } from "../types";
import { inputClass } from "./Field";

interface DeviceRowProps {
  device: Device;
  catalogue: Catalogue | null;
  onSave: (changes: DevicePatch) => Promise<void>;
  onRetire: () => Promise<void>;
}

const smallButton = "rounded px-2 py-1 text-xs hover:bg-burgundy-light";

/** One device in the registry, with in-place editing of Art, Ort and Protokoll. */
export default function DeviceRow({ device, catalogue, onSave, onRetire }: DeviceRowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ kind: device.kind, protocol: device.protocol, location: device.location ?? "" });
  const labelOf = (kind: string) => catalogue?.kinds.find((k) => k.kind === kind)?.label ?? kind;

  function startEditing() {
    setDraft({ kind: device.kind, protocol: device.protocol, location: device.location ?? "" });
    setEditing(true);
  }

  async function save() {
    const location = draft.location.trim();
    try {
      await onSave({ ...draft, location, name: `${labelOf(draft.kind)} ${location}` });
      setEditing(false);
    } catch {
      /* the page shows the error; the row stays in edit mode */
    }
  }

  async function retire() {
    if (window.confirm(`${device.name} (${device.code}) außer Betrieb nehmen? Es bleibt im Register als „außer Betrieb“.`)) {
      await onRetire().catch(() => undefined);
    }
  }

  if (editing) {
    return (
      <tr aria-label={`Gerät ${device.code} bearbeiten`} className="bg-burgundy-light/40">
        <td className="p-2">
          <label className="sr-only" htmlFor={`loc-${device.code}`}>
            Ort
          </label>
          <input
            id={`loc-${device.code}`}
            className={inputClass}
            value={draft.location}
            placeholder="Zimmernummer, Flur o. ä."
            onChange={(e) => setDraft({ ...draft, location: e.target.value })}
          />
        </td>
        <td className="p-2 font-mono text-xs">{device.code}</td>
        <td className="p-2 text-ink/60">{draft.location.trim() ? `${labelOf(draft.kind)} ${draft.location.trim()}` : "–"}</td>
        <td className="p-2">
          <select aria-label="Art" className={inputClass} value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value })}>
            {catalogue?.kinds.map((k) => (
              <option key={k.kind} value={k.kind}>
                {k.label}
              </option>
            ))}
          </select>
        </td>
        <td className="p-2">
          <select aria-label="Protokoll" className={inputClass} value={draft.protocol} onChange={(e) => setDraft({ ...draft, protocol: e.target.value })}>
            {catalogue &&
              Object.entries(catalogue.protocols).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
          </select>
        </td>
        <td className="p-2" />
        <td className="whitespace-nowrap p-2 text-right">
          <button type="button" className={`${smallButton} font-medium text-burgundy`} disabled={!draft.location.trim()} onClick={save}>
            Speichern
          </button>
          <button type="button" className={smallButton} onClick={() => setEditing(false)}>
            Abbrechen
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td className="p-2">{device.location ?? "–"}</td>
      <td className="p-2 font-mono text-xs">{device.code}</td>
      <td className="p-2">{device.name}</td>
      <td className="p-2">{labelOf(device.kind)}</td>
      <td className="p-2">{device.protocol}</td>
      <td className="p-2">
        {device.safety ? (
          <span className="inline-flex items-center gap-1 rounded bg-burgundy-light px-2 py-0.5 text-xs text-burgundy">
            <ShieldAlert size={12} aria-hidden />
            nur lesen
          </span>
        ) : device.controllable ? (
          <span className="text-xs">steuerbar</span>
        ) : (
          <span className="text-xs text-ink/60">nur lesen</span>
        )}
      </td>
      <td className="whitespace-nowrap p-2 text-right">
        <button type="button" className={smallButton} onClick={startEditing} aria-label="Bearbeiten" title="Bearbeiten">
          <Pencil size={14} aria-hidden />
        </button>
        <button type="button" className={smallButton} onClick={retire} aria-label="Außer Betrieb nehmen" title="Außer Betrieb nehmen">
          <PowerOff size={14} aria-hidden />
        </button>
      </td>
    </tr>
  );
}
